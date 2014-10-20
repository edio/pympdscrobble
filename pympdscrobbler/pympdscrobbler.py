from pympdscrobbler.model import ScrobblingMachine
from pympdscrobbler.mpdlistener import MpdListener
from pympdscrobbler.scrobble import SimpleLogScrobbler
from pympdscrobbler.transform import TagGuesser


def main():
    mpd = MpdListener()
    mpd.connect()

    ss = SimpleLogScrobbler()
    ss.login("lastfmuser", "lastfmpassword")

    status = mpd.status()
    sm = ScrobblingMachine(status[0], status[1], transformer=TagGuesser(["(?P<artist>.*) - (?P<title>.*)"]),
                           scrobbler=ss)

    mpd.listen('player', sm.onevent)


if __name__ == '__main__':
    main()
