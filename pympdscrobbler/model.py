import logging
import time
from pympdscrobbler.transform import SongTransformer
from pympdscrobbler.scrobble import SimpleLogScrobbler

NEW_SONG_THRESHOLD = 1000  # ms
MAX_SCROBBLING_THRESHOLD = 4 * 60 * 1000  # 4 mins as required by last.fm documentation
MIN_SCROBBLING_THRESHOLD = 15 * 1000  # shortest track is 30 sec. This is equivalent to 15 seconds of listening
MIN_SCROBBLING_LENGTH = 30 * 1000  # shortest track is 30 sec.

STOP = "stop"
PLAY = "play"
PAUSE = "pause"


def current_time_millis():
    return int(round(time.time() * 1000))


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
        return isinstance(other, State) and self.name == other.name and self.start == other.start


class ScrobblingMachine:
    """
    Holds scrobbling state. Decides, whether playing notification should be sent and scrobbling should be commited
    """

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
            self.state = State(PAUSE)
        else:
            self.song = song
            self.elapsed += self.state.duration()
            self.state = State(PAUSE)

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
        self.state = State(PLAY)
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
            self.state = State(PLAY)
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
        self.state = State(STOP)

    def scrobble_if_needed(self):
        song = self.song
        self.logger.debug("Asked to scrobble {}", song)
        if song and song.eligibleforscrobbling and (self.elapsed > self.scrobblethreshold(song)):
            self.scrobbler.scrobble(song, self.start/1000)

    def nowplaying_if_needed(self):
        song = self.song
        self.logger.debug("Asked to nowplaying {}", song)
        if song and song.eligibleforscrobbling():
            self.scrobbler.nowplaying(song)

    # song utility methods

    def scrobblethreshold(self, song: Song):
        if song.isstream:
            return MIN_SCROBBLING_THRESHOLD
        else:
            threshold = max(MIN_SCROBBLING_THRESHOLD, song.length / 2)
            return min(threshold, MAX_SCROBBLING_THRESHOLD)
