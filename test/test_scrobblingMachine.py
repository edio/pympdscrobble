from unittest import TestCase
import pympdscrobbler
from pympdscrobbler import *


def mocktime(seconds: int):
    pympdscrobbler.current_time_millis = lambda: seconds * 1000


def play():
    return Status({'state': PLAY, 'elapsed': '0.001'})


def seek(sec: int):
    return Status({'state': PLAY, 'elapsed': "{:.3f}".format(sec)})


def stop():
    return Status({'state': STOP})


def pause(sec: int):
    return Status({'state': PAUSE, 'elapsed': "{:.3f}".format(sec)})


songs = [
    Song({'title': "Beyong The Sea", 'artist': "The Chessnuts", 'file': "Track01.flac", 'time': "177"}),
    Song({'title': "Real Fine Frame", 'artist': "Budy Johnson", 'file': "Track02.flac", 'time': "116"})
]

# TODO test with stream
stream = [
    Song({'title': "Three Faces", 'artist': "Dohuke Ballet", 'file': "http://goaradio"}),
    Song({'title': "Three Faces", 'artist': "Dohuke Ballet", 'file': "http://goaradio"}),
]


class TestScrobblingMachine(TestCase):
    def test_stop_play_seek_pause_stop(self):
        scrobbled = []
        played = []

        mocktime(0)
        m = ScrobblingMachine()
        m.scrobble = lambda s: scrobbled.append(s)
        m.nowplaying = lambda s: played.append(s)
        self.assertEqual(m.State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(0, len(played))

        mocktime(10)
        m.onevent(play(), songs[0])
        self.assertEqual(m.State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(1, len(played))

        mocktime(30)
        m.onevent(seek(60), songs[0])
        self.assertEqual(m.State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(1, len(played))

        mocktime(60)
        m.onevent(pause(90), songs[0])
        self.assertEqual(m.State(PAUSE, 60000), m.state)
        self.assertEqual(50000, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(1, len(played))

        mocktime(200)
        m.onevent(stop(), songs[0])
        self.assertEqual(m.State(STOP, 200000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(1, len(played))

    def test_stop_play1_scrobble_play2(self):
        scrobbled = []
        played = []

        mocktime(0)
        m = ScrobblingMachine()
        m.scrobble = lambda s: scrobbled.append(s)
        m.nowplaying = lambda s: played.append(s)
        self.assertEqual(m.State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(0, len(played))

        mocktime(10)
        m.onevent(play(), songs[0])
        self.assertEqual(m.State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(1, len(played))

        mocktime(277)
        m.onevent(play(), songs[1])
        self.assertEqual(m.State(PLAY, 277000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(1, len(scrobbled))
        self.assertEqual(2, len(played))

    def test_pause_stop_scrobble(self):
        scrobbled = []
        played = []

        mocktime(0)
        m = ScrobblingMachine(pause(98), songs[0])
        m.scrobble = lambda s: scrobbled.append(s)
        m.nowplaying = lambda s: played.append(s)
        self.assertEqual(m.State(PAUSE, 0), m.state)
        self.assertEqual(98000, m.elapsed)
        self.assertEqual(0, len(scrobbled))
        self.assertEqual(0, len(played))

        mocktime(10)
        m.onevent(stop(), songs[0])
        self.assertEqual(m.State(STOP, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertEqual(1, len(scrobbled))
        self.assertEqual(0, len(played))


