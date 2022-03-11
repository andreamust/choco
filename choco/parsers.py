
import re
import urllib
import logging

from pyRealParser import Tune

logger = logging.getLogger("choco.parsers")


class ChoCoTune(Tune):

    @classmethod
    def _get_measures(cls, chord_string):
        """
        Splits a chord string into a list of measures, where empty measures are
        discarded. Cleans up the chord string, removes annotations, and handles
        repeats & codas as well.
        :param chord_string: A chord string
        :return: A list of measures, with the contents of every measure as a string
        """
        chord_string = cls._cleanup_chord_string(chord_string)
        chord_string = cls._remove_annotations(chord_string)
        chord_string = cls._fill_long_repeats(chord_string)
        chord_string = cls._fill_codas(chord_string)
        measures = re.split(r'\||LZ|K|Z|{|}|\[|\]', chord_string)
        measures = [m.strip() for m in measures if m.strip() != '']
        measures = cls._fill_single_double_repeats(measures)
        measures = cls._fill_slashes(measures)

        return measures
    
    @staticmethod
    def parse_ireal_url(url):
        """
        Parses iReal urls into human- and machine-readable formats.

        :param url: A url containing one or more tunes
        :return: A list of Tune objects
        """
        url = urllib.parse.unquote(url)
        match = re.match(r'irealb://([^"]+)', url)
        if match is None:
            raise RuntimeError('Provided string is not a valid iReal url!')
        # split url into individual songs along ===
        songs = re.split("===", match.group(1))
        tunes = []
        for song in songs:
            if song != '':
                try:
                    tune = ChoCoTune(song)
                    tunes.append(tune)
                    logger.info('Parsed {}'.format(tune.title))
                except Exception as err:
                    logger.warn(f'Could not import {song}: {err}')
        
        return tunes