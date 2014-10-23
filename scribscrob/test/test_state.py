from unittest import TestCase, mock
from scribscrob.model import Song, Status, PLAY, STOP, PAUSE
from scribscrob.state import ScrobblingMachine, State, eligibleforscrobbling
import scribscrob.state


def mocktime(millis: int):
    scribscrob.state.current_time_millis = lambda: millis


def play(sec: float=0.001):
    return Status({'state': PLAY, 'elapsed': "{:.3f}".format(sec)})


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

bad_songs = [
    Song({'title': None, 'artist': "The Chessnuts", 'file': "Track01.flac", 'time': "177"}),
    Song({'title': "Foothill Boogie", 'artist': None, 'file': "Track02.flac", 'time': "116"}),
    Song({'title': "Intro", 'artist': "Budy Johnson", 'file': "Track03.flac", 'time': "12"})
]

stream = [
    Song({'title': "Blip Blop", 'artist': "Bill Doggett", 'file': "http://rocknrollradio"}),
    Song({'title': "No way out", 'artist': "The Big Six", 'file': "http://rocknrollradio"}),
]


class TestScrobblingMachine(TestCase):
    def test_stop_play_seek_pause_stop(self):
        mocktime(0)
        scrobbler = mock.MagicMock()
        m = ScrobblingMachine(scrobbler=scrobbler)
        self.assertEqual(State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertListEqual(m.scrobbler.call_args_list, [])

        calls = [mock.call.nowplaying(songs[0])]

        mocktime(10000)
        m.onevent(play(), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(30000)
        m.onevent(seek(60), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(60000)
        m.onevent(pause(90), songs[0])
        self.assertEqual(State(PAUSE, 60000), m.state)
        self.assertEqual(50000, m.elapsed)
        scrobbler.assert_has_calls(calls)

        mocktime(200000)
        m.onevent(stop(), songs[0])
        self.assertEqual(State(STOP, 200000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

    def test_stop_play1_scrobble_play2(self):
        mocktime(0000)
        scrobbler = mock.MagicMock()
        m = ScrobblingMachine(scrobbler=scrobbler)
        self.assertEqual(State(STOP, 0), m.state)
        self.assertEqual(0, m.elapsed)
        self.assertListEqual(scrobbler.mock_calls, [])

        calls = [mock.call.nowplaying(songs[0])]

        mocktime(10000)
        m.onevent(play(), songs[0])
        self.assertEqual(State(PLAY, 10000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

        calls.append(mock.call.scrobble(songs[0], 10.0))
        calls.append(mock.call.nowplaying(songs[1]))

        mocktime(277000)
        m.onevent(play(), songs[1])
        self.assertEqual(State(PLAY, 277000), m.state)
        self.assertEqual(0, m.elapsed)
        scrobbler.assert_has_calls(calls)

    def test_pause_stop_scrobble(self):
        mocktime(100000)
        m = ScrobblingMachine(pause(98), songs[0], scrobbler=mock.MagicMock())
        self.assertEqual(State(PAUSE, 100000), m.state)
        self.assertEqual(98000, m.elapsed)
        m.scrobbler.assert_has_calls([])

        mocktime(110000)
        m.onevent(stop(), songs[0])
        self.assertEqual(State(STOP, 110000), m.state)
        self.assertEqual(0, m.elapsed)
        m.scrobbler.assert_has_calls([mock.call.scrobble(songs[0], 2.0)])

    def test_play_stop(self):
        mocktime(100000)
        m = ScrobblingMachine(play(98), songs[0], scrobbler=mock.MagicMock())
        self.assertEqual(State(PLAY, 100000), m.state)
        self.assertEqual(98000, m.elapsed)
        m.scrobbler.assert_has_calls([mock.call.nowplaying(songs[0])])

        mocktime(110000)
        m.onevent(stop(), songs[0])
        self.assertEqual(State(STOP, 110000), m.state)
        self.assertEqual(0, m.elapsed)
        m.scrobbler.assert_has_calls([mock.call.scrobble(songs[0], 2.0)])


class TestUtil(TestCase):
    def test_eligibleforscrobbling(self):
        for s in songs:
            self.assertTrue(eligibleforscrobbling(s))

        for s in stream:
            self.assertTrue(eligibleforscrobbling(s))

        for s in bad_songs:
            self.assertFalse(eligibleforscrobbling(s))



