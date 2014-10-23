from scribscrob.mpdlistener import MpdListener
from scribscrob.state import ScrobblingMachine
from scribscrob.scrobble import LastfmScrobbler
from scribscrob.transform import TagGuesser


def main():
    mpd = MpdListener()
    mpd.connect()

    ss = LastfmScrobbler()
    ss.login("lastfmuser", "lastfmpassword")

    status, song = mpd.status()
    sm = ScrobblingMachine(status, song, transformer=TagGuesser(["(?P<artist>.+) - (?P<title>.+)"]),
                           scrobbler=ss)

    mpd.listen('player', sm.onevent)


if __name__ == '__main__':
    main()
