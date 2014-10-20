from unittest import TestCase, mock
from pympdscrobbler import model
from pympdscrobbler.model import Song, Status, ScrobblingMachine, PLAY, STOP, PAUSE, State
import pympdscrobbler.pympdscrobbler


def mocktime(seconds: int):
    model.current_time_millis = lambda: seconds * 1000


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
        scrobbler = mock.MagicMock()
        m = ScrobblingMachine(scrobbler=scrobbler)
        self.assertEqual(State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertListEqual(m.scrobbler.call_args_list, [])

        calls = [mock.call.nowplaying(songs[0])]

        mocktime(10)
        m.onevent(play(), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(30)
        m.onevent(seek(60), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(60)
        m.onevent(pause(90), songs[0])
        self.assertEqual(State(PAUSE, 60000), m.state)
        self.assertEqual(50000, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(200)
        m.onevent(stop(), songs[0])
        self.assertEqual(State(STOP, 200000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

    def test_stop_play1_scrobble_play2(self):
        mocktime(0)
        scrobbler = scrobbler = mock.MagicMock()
        m = ScrobblingMachine(scrobbler=scrobbler)
        self.assertEqual(State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertListEqual(scrobbler.mock_calls, [])

        calls = [mock.call.nowplaying(songs[0])]

        mocktime(10)
        m.onevent(play(), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        calls.append(mock.call.scrobble(songs[0], 10.0))
        calls.append(mock.call.nowplaying(songs[1]))

        mocktime(277)
        m.onevent(play(), songs[1])
        self.assertEqual(State(PLAY, 277000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

    def test_pause_stop_scrobble(self):
        scrobbled = []
        played = []

        mocktime(0)
        m = ScrobblingMachine(pause(98), songs[0], scrobbler=mock.MagicMock())
        self.assertEqual(State(PAUSE, 0), m.state)
        self.assertEqual(98000, m.elapsed)
        m.scrobbler.assert_has_calls([])

        mocktime(10)
        m.onevent(stop(), songs[0])
        self.assertEqual(State(STOP, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        m.scrobbler.assert_has_calls([mock.call.scrobble(songs[0], -98.0)])


