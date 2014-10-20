import pylast


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

    def scrobble(self, song, timestamp):
        self.network.scrobble(song.artist, song.title, timestamp)

    def nowplaying(self, song):
        self.network.update_now_playing(song.artist, song.title)