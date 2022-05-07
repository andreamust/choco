import os

from lark.exceptions import UnexpectedInput

from choco.converters import Converter
from choco.converters.lark_converters.lark_to_harte import Encoder
from choco.converters.lark_converters.lark_converter import Parser
from choco.converters.utils import open_stats_file
from choco.converters.polychord_converter import convert_polychord

basedir = os.path.dirname(__file__)
LEADSHEET_CHORD_STATS = os.path.join(basedir, "../../../partitions/wikifonia/choco/chord_stats.csv")
ABC_CHORD_STATS = os.path.join(basedir, "../../../partitions/nottingham/choco/chord_stats.csv")

leadsheet_music21_parser = Parser("leadsheet_music21")
abc_music21_parser = Parser("abc_music21")
harte_encoder = Encoder()


def test_leadsheet_harte_conversion(stats_file: str) -> None:
    """
    Tests the Leadsheet chord converter using the statistics file generated by stats.py.
    """
    leadsheet_converter = Converter(leadsheet_music21_parser, harte_encoder)

    all_leadsheet_chord = open_stats_file(stats_file)

    f = 0
    for chord_data in all_leadsheet_chord[:500]:
        try:
            converted_chord = leadsheet_converter.convert(chord_data[0])
            f += float(chord_data[2])
            print(f"{chord_data[0].ljust(15)} -> {converted_chord}")
        except UnexpectedInput as lark_e:
            # parser error -> chord couldnt be parsed
            # print(f"{chord_data[0].ljust(15)} -> Parsing error")
            print(convert_polychord(chord_data[0]))
            pass
        except Exception as e:
            print(e)
    print(f)


def test_abc_harte_conversion(stats_file: str) -> None:
    """
    Tests the ABC chord converter using the statistics file generated by stats.py.
    """
    abc_converter = Converter(abc_music21_parser, harte_encoder)

    all_abc_chord = open_stats_file(stats_file)

    f = 0
    for chord_data in all_abc_chord:
        try:
            converted_chord = abc_converter.convert(chord_data[0])
            f += float(chord_data[2])
            # print(f"{chord_data[0].ljust(15)} -> {converted_chord}")
        except UnexpectedInput as lark_e:
            # parser error -> chord can't be parsed
            # print(f"{chord_data[0].ljust(15)} -> Parsing error")
            pass
        except Exception as e:
            print(e)
    print(f)


if __name__ == '__main__':
    test_leadsheet_harte_conversion(os.path.join(basedir, LEADSHEET_CHORD_STATS))
    # print(convert_roman_numeral('ii', '#', ['G#', 'minor']))

    # test_abc_harte_conversion(os.path.join(basedir, ABC_CHORD_STATS))
