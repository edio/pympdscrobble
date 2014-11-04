import logging
import json
import os

import pylast
from scribscrob.model import Song


API_KEY = "key"
API_SECRET = "secret"

logger = logging.getLogger(__name__)

TMP_FILE_SUFFIX = ".tmp"


class LastfmScrobbler:
    """
    Scrobbles to last.fm
    """

    def __init__(self, username, password: str=None, password_hash: str=None, cachefile: str=None):
        self.username = username
        self.password_hash = password_hash if password_hash else pylast.md5(password)
        self.cachefile = cachefile
        self.network = None

    def ensurestarted(self):
        if not self.network:
            self.network = pylast.LastFMNetwork(api_key=API_KEY,
                                                api_secret=API_SECRET,
                                                username=self.username,
                                                password_hash=self.password_hash)

    def scrobble(self, song, timestamp):
        """
        Scrobbles track. Stores it to local cache if any last.fm related error occurs
        """
        try:
            self._scrobble(song, timestamp)
            self.flush_cache()
        except (pylast.WSError, pylast.NetworkError, pylast.MalformedResponseError) as e:
            logger.error("Can't scrobble. Saving to local cache", e)
            self.scrobble_to_file(song, timestamp)

    def _scrobble(self, song, timestamp):
        """
        Just plain call to API without error handling
        """
        self.ensurestarted()
        self.network.scrobble(song.artist, song.title, timestamp)
        logger.debug("Scrobbled %s", song)

    def nowplaying(self, song):
        try:
            self.ensurestarted()
            self.network.update_now_playing(song.artist, song.title)
            logger.debug("Sent now playing %s", song)
        except (pylast.WSError, pylast.NetworkError, pylast.MalformedResponseError) as e:
            logger.error("Can't send now playing notification", e)

    def scrobble_to_file(self, song: Song, start):
        mode = 'a' if os.path.isfile(self.cachefile) else 'x'
        with open(self.cachefile, mode=mode) as f:
            print(song)
            d = {"song": song,
                 "start": start}
            json.dump(d, f, separators=(',', ':'), sort_keys=True)
            f.write('\n')

    def flush_cache(self):
        if self.cachefile:
            with open(self.cachefile, mode='r') as cachefile_handle:
                scrobbled = self.scrobble_cache_file(cachefile_handle)
                if scrobbled:
                    with open(self.get_tmp_cache(), mode="w") as tmp_cache_file_handle:
                        for line in cachefile_handle:
                            tmp_cache_file_handle.write(line)

            os.rename(self.get_tmp_cache(), self.cachefile)

    def get_tmp_cache(self):
        return self.cachefile + TMP_FILE_SUFFIX

    def scrobble_cache_file(self, fp):
        scrobbled = 0
        try:
            for line in fp:
                d = json.loads(line)
                song = d['song']
                start = d['start']
                self._scrobble(song, start)
                scrobbled += 1
        except (pylast.WSError, pylast.NetworkError, pylast.MalformedResponseError) as e:
            logger.error("Can't scrobble from local cache", e)
        return scrobbled

