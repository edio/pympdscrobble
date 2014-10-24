STOP = "stop"
PLAY = "play"
PAUSE = "pause"


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

    def __repr__(self):
        nstr = lambda s: s if s else "<empty>"
        source = "[http]" if self.isstream else "[file]"
        return "{:s} {:s} - {:s}".format(source, nstr(self.artist), nstr(self.title))


class Status:
    """
    Simple structure over status dict returned by MPDClient
    """

    def __init__(self, status: dict):
        self.state = status['state']
        self.elapsed = status['elapsed'] if self.state != STOP else None

    def __str__(self):
        return "{:s}({:s})".format(self.state, self.elapsed if self.elapsed else "")
