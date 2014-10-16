import os

__author__ = 'edio'

from select import select
from mpd import MPDClient
from configparser import ConfigParser
import logging
import time
import pylast
import re

logger = logging.getLogger(__name__)

STOP = "stop"
PLAY = "play"
PAUSE = "pause"
NEW_SONG_THRESHOLD = 1000  # ms
MAX_SCROBBLING_THRESHOLD = 4 * 60 * 1000  # 4 mins as required by last.fm documentation
MIN_SCROBBLING_THRESHOLD = 15 * 1000  # shortest track is 30 sec. This is equivalent to 15 seconds of listening
MIN_SCROBBLING_LENGTH = 30 * 1000  # shortest track is 30 sec.


class Song:
    """
    Simple structure over currentsong dict returned by MPDClient
    """

    def __init__(self, song: dict):
        """
        Create instance from dictionary returned by MPDClient
        """
        # primary
        self.title = song.get('title')
        self.artist = song.get('artist')
        self.album = song.get('album')
        self.file = song.get('file')

        # derived
        self.isstream = self.file.startswith('http')
        if not self.isstream:
            self.length = int(song['time']) * 1000

    def eligibleforscrobbling(self):
        return self.artist and self.title and (self.isstream or self.length > MIN_SCROBBLING_LENGTH)

    def __str__(self):
        nstr = lambda s: s if s else "<empty>"
        source = "[http]" if self.isstream else "[file]"
        return "{:s} {:s} - {:s}".format(source, nstr(self.artist), nstr(self.title))


class Status:
    """
    Simple structure over status dict returned by MPDClient
    """

    def __init__(self, status: dict):
        self.state = status['state']
        if self.state != STOP:
            self.elapsed = status['elapsed']


class SongTransformer:
    """
    Transforms song (i.e. guesses tags). Intended for extension
    """

    def transform(self, song: Song):
        """
        Dummy transformer. Does nothing
            param: song - song to transform
            returns: same song instance
        """
        return song


class TagGuesser(SongTransformer):
    """
    Transformers that guesses tags
    """

    def __init__(self, regexes: list):
        self.patterns = list(map(lambda r: re.compile(r), regexes))

    def transform(self, song: Song):
        if song.title and song.artist:
            # nothing to do
            return song

        name = song.title if song.title else os.path.basename(song.file)
        for p in self.patterns:
            m = p.match(name)
            if m:
                artist = m.group('artist')
                title = m.group('title')
                if artist and title:
                    song.artist = artist
                    song.title = title
                    return song
        return song  # failed to guess


class MPD:
    """
    Responsible for communication with MPD. Provides refined abstraction over MPDClient
    """

    logger = logging.getLogger('mpd')

    def __init__(self, host: str='localhost', port: int=6600, password: str=None):
        # TODO support passwords
        self.client = MPDClient()
        self.host = host
        self.port = port
        self.password = password
        pass

    def connect(self):
        """
        Just performs a connection attempt with host, port and password passed to constructor
        """
        self.client.connect(self.host, self.port)
        self.logger.info("Connected to {}:{}", self.host, self.port)

    def listen(self, event, onevent):
        """
        listens to MPD events and calls onevent callback with current state name and current song
        """
        while True:
            self.client.send_idle()
            canRead = select([self.client], [], [])[0]
            if canRead:
                changes = self.client.fetch_idle()
                if changes.count(event) > 0:
                    onevent(*self.status())

    def status(self):
        status = self.client.status()
        song = self.client.currentsong()
        self.logger.debug("Current status {} {}", status['state'], song)
        return Status(status), Song(song)


class SimpleLogScrobbler:
    """
    Scrobbles to last.fm. Stores to local
    """

    API_KEY = "apikey"
    API_SECRET = "secret"

    def login(self, username: str, password: str):
        password_hash = pylast.md5(password)
        self.network = pylast.LastFMNetwork(api_key=self.API_KEY, api_secret=self.API_SECRET, username=username,
                                            password_hash=password_hash)

    def scrobble(self, song: Song, timestamp):
        self.network.scrobble(song.artist, song.title, timestamp)

    def nowplaying(self, song: Song):
        self.network.update_now_playing(song.artist, song.title)


class ScrobblingMachine:
    """
    Holds scrobbling state. Decides, whether playing notification should be sent and scrobbling should be commited
    """

    class State:
        def __init__(self, name, start: int=None):
            self.name = name
            if not start:
                start = current_time_millis()
            self.start = start

        def ispause(self):
            return self.name == PAUSE

        def isplay(self):
            return self.name == PLAY

        def isstop(self):
            return self.name == STOP

        def duration(self):
            return current_time_millis() - self.start

        def __repr__(self):
            return str(self.start) + ":" + self.name

        def __eq__(self, other):
            return isinstance(other, ScrobblingMachine.State) and self.name == other.name and self.start == other.start

    logger = logging.getLogger("scrobbler")

    state = None
    song = None
    elapsed = 0
    start = -1

    def __init__(self, initialstatus: Status=Status({'state': STOP}), initialsong: Song=None,
                 transformer: SongTransformer=SongTransformer(),
                 scrobbler: SimpleLogScrobbler=None):
        self.transformer = transformer
        self.scrobbler = scrobbler
        self.onevent(initialstatus, initialsong)

    def onevent(self, status: Status, song: Song):
        state = status.state

        if state == STOP:
            self.stop()
        else:
            song = self.transformer.transform(song)
            elapsed = int(float(status.elapsed) * 1000)
            if state == PLAY and (song.isstream or elapsed <= NEW_SONG_THRESHOLD):
                self.play(song)
            elif state == PLAY and elapsed > NEW_SONG_THRESHOLD:
                self.play_continue(song, elapsed)
            elif state == PAUSE:
                self.pause(song, elapsed)
            else:
                raise Exception("Unknown state " + state)  # TODO

    def pause(self, song, elapsed):
        """
        Handle pause
            param: song - paused song
        """
        # If we connected in the middle
        if not self.state:
            self.song = song
            self.elapsed = elapsed
            self.start = current_time_millis() - elapsed
            self.state = self.State(PAUSE)
        else:
            self.song = song
            self.elapsed += self.state.duration()
            self.state = self.State(PAUSE)

    def play(self, song):
        """
        Handle play from beginning
            param song - played song
        """
        # if we had been playing something
        if self.state and self.state.isplay():
            # count this time as played
            self.elapsed += self.state.duration()

        # ... or been on pause
        if self.state and (self.state.isplay() or self.state.ispause()):
            # scrobble what've been played
            self.scrobble_if_needed()

        # ... or been stopped
        self.song = song
        self.elapsed = 0
        self.start = current_time_millis()
        self.state = self.State(PLAY)
        self.nowplaying_if_needed()

    def play_continue(self, song, elapsed):
        """
        Handle play after pause/seek
            param: song - seeked/unpaused song
        """
        # We connected in the middle of play
        if not self.state:
            self.song = song
            self.elapsed = elapsed
            self.start = current_time_millis() - elapsed
            self.state = self.State(PLAY)
            self.nowplaying_if_needed()

        # If we've been on pause before
        if self.state.ispause():
            # send now playing if previous have been timed out
            self.nowplaying_if_needed()

    def stop(self):
        """
        Handle stop
        """
        # just scrobble current song if any and update current state
        self.scrobble_if_needed()
        self.song = None
        self.elapsed = 0
        self.state = self.State(STOP)

    def scrobble_if_needed(self):
        song = self.song
        self.logger.debug("Asked to scrobble {}", song)
        if song and song.eligibleforscrobbling and (self.elapsed > self.scrobblethreshold(song)):
            self.scrobble(song, self.start)

    def nowplaying_if_needed(self):
        song = self.song
        self.logger.debug("Asked to nowplaying {}", song)
        if song and song.eligibleforscrobbling():
            self.nowplaying(song)

    # song utility methods

    def scrobblethreshold(self, song: Song):
        if song.isstream:
            return MIN_SCROBBLING_THRESHOLD
        else:
            threshold = max(MIN_SCROBBLING_THRESHOLD, song.length / 2)
            return min(threshold, MAX_SCROBBLING_THRESHOLD)

    # calls to lastfm

    def nowplaying(self, song: Song):
        print("Now plaing", song)
        self.scrobbler.nowplaying(song)

    def scrobble(self, song: Song, start):
        print("Scrobbling", song)
        self.scrobbler.scrobble(song, int(start / 1000))


def main():
    mpd = MPD()
    mpd.connect()

    ss = SimpleLogScrobbler()
    ss.login("lastfmuser", "lastfmpassword")

    status = mpd.status()
    sm = ScrobblingMachine(status[0], status[1], transformer=TagGuesser(["(?P<artist>.*) - (?P<title>.*)"]),
                           scrobbler=ss)

    mpd.listen('player', sm.onevent)


def current_time_millis():
    return int(round(time.time() * 1000))


if __name__ == '__main__':
    main()
