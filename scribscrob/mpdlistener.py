import logging
from select import select
from mpd import MPDClient
from scribscrob.model import Status, Song


logger = logging.getLogger('mpd')


class MpdListener:
    """
    Responsible for communication with MPD. Provides refined abstraction over MPDClient
    """

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
        logger.info("Connected to %s:%d", self.host, self.port)

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
        logger.debug("Current status %s %s", status['state'], song)
        return Status(status), Song(song) if song else None