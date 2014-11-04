from configparser import ConfigParser
from unittest import TestCase
from scribscrob import ScribScrobFactory


class TestScribScrobFactory(TestCase):
    config = ConfigParser(allow_no_value=True, strict=False)
    config.read('scribscrob.ini')
    factory = ScribScrobFactory(config)

    def test_get_mpd(self):
        mpd = self.factory.get_mpd()
        self.assertIsNotNone(mpd)

    def test_get_lastfm(self):
        lastfm = self.factory.get_lastfm()
        self.assertIsNotNone(lastfm)

    def test_get_transformer(self):
        tagguesser = self.factory.get_transformer()
        self.assertIsNotNone(tagguesser)
        self.assertEqual(2, len(tagguesser.patterns))
