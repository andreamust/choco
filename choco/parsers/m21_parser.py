"""
Utilities for extracting chord annotations from notated music and symbolic files
that can be processed and loosslessly converted with music21.

```
>>> c = music21.converter.Converter()
>>> for sc in c.defaultSubconverters():
>>> ...     print(sc)
```
<class 'music21.converter.subConverters.ConverterABC'>
<class 'music21.converter.subConverters.ConverterBraille'>
<class 'music21.converter.subConverters.ConverterCapella'>
<class 'music21.converter.subConverters.ConverterClercqTemperley'>
<class 'music21.converter.subConverters.ConverterHumdrum'>
<class 'music21.converter.subConverters.ConverterIPython'>
<class 'music21.converter.subConverters.ConverterLilypond'>
<class 'music21.converter.subConverters.ConverterMEI'>
<class 'music21.converter.subConverters.ConverterMidi'>
<class 'music21.converter.subConverters.ConverterMuseData'>
<class 'music21.converter.subConverters.ConverterMusicXML'>
<class 'music21.converter.subConverters.ConverterNoteworthy'>
<class 'music21.converter.subConverters.ConverterNoteworthyBinary'>
<class 'music21.converter.subConverters.ConverterRomanText'>
<class 'music21.converter.subConverters.ConverterScala'>
<class 'music21.converter.subConverters.ConverterText'>
<class 'music21.converter.subConverters.ConverterTextLine'>
<class 'music21.converter.subConverters.ConverterTinyNotation'>
<class 'music21.converter.subConverters.ConverterVexflow'>
<class 'music21.converter.subConverters.ConverterVolpiano'>
<class 'music21.converter.subConverters.SubConverter'>

See: https://web.mit.edu/music21/doc/moduleReference/moduleConverter.html

Notes
-----
    - Score expansion may produce inconsistent measure numbers: flatten out.
    - The first measure after the expansion may have implicit rests.
    - Handling expansion errors for the construction of the performed score.

"""
import re
import logging
from typing import List, Tuple

import jams
from music21 import converter
from music21.chord import Chord
from music21.harmony import ChordSymbol
from music21.key import Key, KeySignature
from music21.meter import TimeSignature
from music21.metadata import Metadata
from music21.stream import Score, Part, Measure

from music21.repeat import Expander, ExpanderException


logger = logging.getLogger("choco.music21_parser")


class NoChordsInScoreException(Exception):
    """Raised when no part with chords is found in a score"""
    pass


def process_score(score, expand=True, rename_measures=True) -> Tuple:
    """
    Extract metadata and chord annotations from a score that can be processed
    via music21. The timing information of chords is currently given in 
    (measure, offset) and the score is first expanded to flatten any repetition,
    assuming that the notation is consistent.

    Parameters
    ----------
    score : str or `music21.Score`
        The single piece to be processed, either given as a file path reference
        or as a `music21.Score` object that has already been parsed.

    Returns
    -------
    metadata : dict
        A dictionary with all the metadata associated to the tune, including
        title, name of composer, etc. (if available). It also includes a boolean
        placeholder recording whether the score has been expanded or not.
    chord_ann : list of tuples
        A list of (Chord, measure, offset) including all chord annotations.
    time_signature_ann : list of tuples
        A list of (time signature, measure, offset=0) for all time signatures.
    key_signature_ann : list of tuples
        A list of (key signature, measure, offset=0) for all key signatures.

    """
    # Parse the single tune first
    if isinstance(score, str):
        score = converter.parse(score)
    # Avoid corpus or score libraries
    if not isinstance(score, Score) and len(score) > 1:
        raise ValueError("This function expects a single tune")
    # Extract the chord-annpotated part, assert one
    score_parts = score.getElementsByClass(Part)
    chord_parts = [part for part in score_parts \
        if len(part.recurse().getElementsByClass(Chord)) > 0]
    assert len(chord_parts) <= 2, "Multiple parts with chord annotations found"

    if len(chord_parts) == 0:
        raise NoChordsInScoreException("No part with chord annotation found!")

    chord_part = chord_parts[0]  # safe with the assert
    meta = score.getElementsByClass(Metadata)[0]
    composers = meta.composers if meta.composers is not None \
        else [meta.composer]  # always prefer the full list of composers

    metadata = {
        "title": meta.title,
        "composers": composers,
        "movement": meta.movementName,
    }

    # *** ----------------------------------------------- *** #
    # *** Extract all relevant annotations from the score *** #
    # *** ----------------------------------------------- *** #

    if expand:  
        try:  # attempt expanding the score only if requested
            chord_part = Expander(chord_part).process()
            metadata["expanded"] = True
            measure_no = lambda m: m.measureNumberWithSuffix()
        except ExpanderException:
            logger.warn(f"Score {meta.title} has inconsistent repeats")
            measure_no = lambda m: m.measureNumber
            metadata["expanded"] = False

    measure_offmap = chord_part.measureOffsetMap()
    if metadata["expanded"] and rename_measures:
        measure_offmap = {offset: [Measure(m)] for m, offset \
                          in enumerate(measure_offmap.keys())}
    chord_part_duration = chord_part.duration.quarterLength
    metadata["duration"] = chord_part_duration  # XXX can be Fractional!
    metadata["duration_m"] = int(measure_no(  # last measure from offset
        measure_offmap[max(measure_offmap.keys())][-1]))

    time_signatures = chord_part.recurse().getElementsByClass(TimeSignature)
    ts_str = lambda x: f"{x.numerator}/{x.denominator}"
    time_signatures_ann = []

    for time_signature in time_signatures.iter():
        time_signature_str = ts_str(time_signature)
        # Add the time signature if it is not duplicated
        if len(time_signatures_ann) == 0 or \
            time_signatures_ann[-1][0] != time_signature_str:
            # Retrieve the measure name
            time_signatures_ann.append([
                time_signature_str,
                measure_no(measure_offmap[time_signature.offset][0]),
                0,
                chord_part_duration-time_signature.offset,
            ])
            if len(time_signatures_ann) > 1:
                time_signatures_ann[-2][3] = time_signature.offset  # update

    key_signatures = chord_part.recurse().getElementsByClass(KeySignature)
    key_signatures_ann = []

    for key_signature in key_signatures.iter():
        # Key can be either explicit (e.g. G major) or implicit as an actual
        # key signature (e.g. 1 sharp); conversion step required.
        if not isinstance(key_signature, Key):
            key_signature = key_signature.asKey()
        key_signature_str = key_signature.name
        # Add the key signature if it is not duplicated
        if len(key_signatures_ann) == 0 or \
            key_signatures_ann[-1][0] != key_signature_str:
            # Retrieve the measure name
            key_signatures_ann.append([
                key_signature_str,
                measure_no(measure_offmap[key_signature.offset][0]),
                0,
                chord_part_duration-key_signature.offset,
            ])
            if len(key_signatures_ann) > 1:
                key_signatures_ann[-2][3] = key_signature.offset  # update

    chord_ann = []

    for i, measure in enumerate(chord_part.getElementsByClass(Measure)):
        measure_number = i if rename_measures else measure_no(measure)
        measure_duration = measure.duration.quarterLength
        for chord in measure.getElementsByClass(Chord):
            # Check the type of given chord annotation
            if isinstance(chord, ChordSymbol):
                chord_str = chord.figure
            else:  # chord as an ordered list of pitches
                chord_str = ",".join([p.nameWithOctave for p in chord.pitches])
            # Add chord annotation and update duration information
            chord_ann.append([chord_str, measure_number, chord.offset,
                              measure_duration-chord.offset])
            if len(chord_ann) > 1 and chord_ann[-2][1] == measure_number:
                chord_ann[-2][3] = chord.offset  # update previous duration

    return metadata, chord_ann, time_signatures_ann, key_signatures_ann


def process_romantext(romantext, **meta_kwargs):
    """
    Extract metadata and chord annotations from a RomanText annotation via
    music21. Analogously to the score version, timing information is currently
    given in (measure, beat offset) and the score is first expanded to flatten
    any repetition, assuming that the notation is consistent. Also, duration is
    expressed as quarter length. Although this provides some syntactic sugar,
    Roman chord figures are returned along with local key information.

    Parameters
    ----------
    romantext : str or `music21.Score`
        The single piece to be processed, either given as a file path reference
        or as a `music21.Score` object that has already been parsed.
    
    Returns
    -------
    ...

    Notes
    -----
        - This implementation is quite different than that of the score; this
            is because the converter in m21 does not integrate certain info in
            the score (e.g. local keys/modulations are only in the numerals).

    """
    score = converter.parse(romantext, format='romanText') \
        if isinstance(romantext, str) else romantext
    annotator, ann_tools = extract_romantext_annotator(romantext, **meta_kwargs)
    numerals = [x for x in score.recurse().getElementsByClass('RomanNumeral')]
    # Extract the basic metadata that should be provided in the annotation
    meta = score.getElementsByClass(Metadata)[0]
    metadata = {
        "title": meta.title,
        "composers": meta.composers,
        "duration": score.duration.quarterLength,
        "duration_m": len(score.recurse().getElementsByClass(Measure)),
        "annotator": annotator if annotator is not None else "",
        "annotation_tools": ann_tools,
    }
    # XXX Expansion should not be needed before ann extraction if no score
    chord_ann, key_ann = [], []
    for roman_numeral in numerals:
        # Extracting timing information and processing local key
        measure = roman_numeral.getContextByClass('Measure').measureNumber
        offset = roman_numeral.beat
        duration = roman_numeral.quarterLength
        lkey = roman_numeral.key.name.replace('-', 'b')

        chord_ann.append([
            measure, offset, duration,
            lkey + ":" + roman_numeral.figure,
        ])

        if len(key_ann) > 0 and key_ann[-1][-1] == lkey:
            key_ann[-1][2] += duration  # update duration
        else:  # an actual modulation: local key change
            key_ann.append([measure, offset, duration, lkey])

    return metadata, chord_ann, None, key_ann  # TODO


def extract_romantext_annotator(romantext_path, clean_str=False,
    annotation_tool_map:dict={}, annotation_ignore:list=[]):
    """
    Extract annotation information from the RomanText file and attempts
    separating annotator names and annotation tools in the former string.

    Parameters
    ----------
    romantext_path : str
        Path to the text analysis in RomanText to read.
    clean_str : bool
        Whether the annotation string should be processed for disentanbglement.
    
    Returns
    -------
    annotator_str : str
        The annotator string, containing the name only if `clean_str`.
    annotation_tool : str
        Identifier or name of the annotation tool, if specified and recognised.

    """
    with open(romantext_path, "r") as rt_text:
        analysis = "".join(rt_text.readlines())
    # Find the annotator details, all merged in the same line
    annotation_tool = ""  # assumed not available, yet
    annotator_str = re.search("Analyst:(.+)", analysis)
    if annotator_str is not None:  # strip the annotator
        annotator_str = annotator_str.group(1).strip()
    if annotator_str is None or not clean_str:
        return annotator_str, annotation_tool

    for tool_desc, tool_name in annotation_tool_map.items():
        if tool_desc in annotator_str:
            annotation_tool = tool_name
            annotator_str = annotator_str.replace(tool_desc, "")

    for ignore_str in annotation_ignore:
        if ignore_str in annotator_str:  # drop everything after ignore_str
            annotator_str = annotator_str[:annotator_str.find(ignore_str)]

    annotator_str = annotator_str.replace(" and ", ", ")
    return annotator_str, annotation_tool
