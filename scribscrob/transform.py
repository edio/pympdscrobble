import os
import re


#TODO consider support for external transformers (i.e. plugins)
from scribscrob.model import Song


class SongTransformer:
    """
    Transforms song (i.e. guesses tags). Intended for extension
    """

    def transform(self, song):
        """
        Dummy transformer. Does nothing
            param: song - song to transform
            returns: same song instance
        """
        return song


class TagGuesser(SongTransformer):
    """
    SongTransformer implementation, that guesses artist tag from title or filename
    """

    def __init__(self, regexes: list):
        self.patterns = list(map(lambda r: re.compile(r), regexes))

    def transform(self, song: Song):
        if song.title and song.artist:
            # nothing to do
            return song

        name = song.title if song.title else os.path.basename(song.file)
        for p in self.patterns:
            m = p.match(name)
            if m:
                artist = m.group('artist')
                title = m.group('title')
                if artist and title:
                    song.artist = artist
                    song.title = title
                    return song
        return song  # failed to guess