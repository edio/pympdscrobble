from configparser import ConfigParser
import json
import logging
import os
from scribscrob import APP_NAME
from scribscrob.mpdlistener import MpdListener
from scribscrob.state import ScrobblingMachine
from scribscrob.scrobble import LastfmScrobbler
from scribscrob.transform import TagGuesser

logger = logging.getLogger(APP_NAME)

HOME_DIR = "~/.config/scribscrob"
CONFIG_FILE = os.path.join(os.path.expanduser(HOME_DIR), "config.ini")
LOG_FILE = os.path.join(os.path.expanduser(HOME_DIR), "scribscrob.log")


class ScribScrobFactory:
    # mpd
    SECTION_MPD = 'mpd'
    OPT_MPD_HOST = 'host'
    OPT_MPD_PORT = 'port'
    # last.fm
    SECTION_LASTFM = 'last.fm'
    OPT_LASTFM_USER = 'user'
    OPT_LASTFM_PASS = 'password_hash'
    # tag guesser
    SECTION_TAGGUESS = 'tagguess'
    OPT_TAGGUESS_REGEX = 'regexps'

    def __init__(self, config: ConfigParser):
        self.config = config

    def get_mpd(self):
        host = self.config.get(self.SECTION_MPD, self.OPT_MPD_HOST)
        port = self.config.getint(self.SECTION_MPD, self.OPT_MPD_PORT)
        mpd = MpdListener(host, port)
        return mpd

    def get_lastfm(self):
        user = self.config.get(self.SECTION_LASTFM, self.OPT_LASTFM_USER)
        password_hash = self.config.get(self.SECTION_LASTFM, self.OPT_LASTFM_PASS)
        lastfm = LastfmScrobbler(username=user, password_hash=password_hash)
        return lastfm

    def get_transformer(self):
        regexps_raw = self.config.get(self.SECTION_TAGGUESS, self.OPT_TAGGUESS_REGEX)
        regexps = json.loads(regexps_raw)
        tagguesser = TagGuesser(regexps)
        return tagguesser


def config():
    config = ConfigParser(allow_no_value=True, strict=False)
    read = config.read(CONFIG_FILE)
    logger.debug("read configuration from %s", read)
    return config


def main():

    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

    factory = ScribScrobFactory(config())

    mpd = factory.get_mpd()
    # TODO connect implicitly or schedule reconnect if failed
    mpd.connect()

    scrobbler = factory.get_lastfm()

    status, song = mpd.status()
    sm = ScrobblingMachine(status, song, transformer=factory.get_transformer(), scrobbler=scrobbler)

    # TODO figure out smthng to allow running w/o mpd connection
    mpd.listen('player', sm.onevent)


if __name__ == '__main__':
    main()
