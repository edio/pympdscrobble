from abc import ABCMeta, abstractmethod
import logging
import json

import pylast


API_KEY = "apikey"
API_SECRET = "secres"

logger = logging.getLogger(__name__)


class Scrobbler:
    __metaclass__ = ABCMeta

    @abstractmethod
    def scrobble(self, song, start):
        '''
        Scrobble song
            param song: song to scrobble
            param start: utc timestamp in seconds
        '''

    @abstractmethod
    def nowplaying(self, song):
        '''
        Send nowplaying notification
            param song: song that is currently playing
        '''

    @abstractmethod
    def start(self):
        '''
        Start the scrobbler (i.e. perform login, resource handling, etc.)
        '''


class LastfmScrobbler(Scrobbler):
    """
    Scrobbles to last.fm
    """

    def __init__(self, username, password: str=None, password_hash: str=None):
        self.username = username
        self.password_hash = password_hash if password_hash else pylast.md5(password)

    def start(self):
        self.network = pylast.LastFMNetwork(api_key=API_KEY,
                                            api_secret=API_SECRET,
                                            username=self.username,
                                            password_hash=self.password_hash)

    def scrobble(self, song, timestamp):
        self.network.scrobble(song.artist, song.title, timestamp)

    def nowplaying(self, song):
        self.network.update_now_playing(song.artist, song.title)


class FallbackScrobbler(Scrobbler):
    def __init__(self, delegate: Scrobbler, fallbackfile: str):
        self.delegate = delegate
        self.fallbackfile = fallbackfile

    def start(self):
        try:
            self.ensurestarted()
        except pylast.NetworkError or pylast.WSError as e:
            logger.error("Can't login to last.fm", e)

    def scrobble(self, song, start):
        try:
            self.ensurestarted()
            self.delegate.scrobble(song, start)
        except pylast.NetworkError or pylast.WSError as e:
            logger.error("Can't scrobble to last.fm", e)
            self.scrobble_to_file(song, start)

    def nowplaying(self, song):
        try:
            Scrobbler.nowplaying(self, song)
        except pylast.NetworkError or pylast.WSError as e:
            logger.error("Can't login to last.fm", e)

    def ensurestarted(self):
        if not self.started:
            self.delegate.start()
            self.started = True

    def scrobble_to_file(self, song, start):
        with open(self.fallbackfile) as f:
            d = {"artist": song.artist,
                 "title": song.title,
                 "start": start}
            json.dump(d, f)
