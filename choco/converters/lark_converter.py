"""
Chord converter based on Lark Grammar.
So far, the following converters have been implemented:
    - leadsheet converter
    - ABC converter
"""

from choco.converters.grammar.abc import abc_music21
from choco.converters.grammar.leadsheet import leadsheet_music21
from choco.converters.parser import BaseParser


class Parser(BaseParser):
    def __init__(self, dialect: str):
        """
        Build parser with specified dialect

        Parameters
        ----------
        dialect : str
            Leadsheet dialect that needs to be used
        """
        DIALECT_MAP = {
            "leadsheet_music21": leadsheet_music21,
            "abc_music21": abc_music21,
        }

        super().__init__(DIALECT_MAP[dialect])
