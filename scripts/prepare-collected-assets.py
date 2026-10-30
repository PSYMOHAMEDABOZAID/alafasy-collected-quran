1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
#!/usr/bin/env python3
"""Package the original Alafasy v1.0.0 MP3 and ayah-timing ZIP archives.

Requires Python 3.10+ and ffprobe (provided by ffmpeg).
It does not alter, replace or estimate audio/timing data. On validation failure,
GitHub Actions must not upload anything from the prepared output.
"""

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

VERSION = 'SYNTAX_AND_TIMINGS_VERIFIED_V5_2026_10_31'
EXPECTED_AYAH_TOTAL = 6236  # Hafs convention (114 surahs)


def normalize_digits(s: str) -> str:
    """Translate Arabic-Indic/extended Arabic-Indic numerals, preserving filenames."""
    result = []
    for ch in s:
        try:
            result.append(str(unicodedata.decimal(ch)))
        except ValueError:
            result.append(ch)
    return ''.join(result)


def surah_number(filename: str, suffix: str):
    """Match 001.mp3, 088الغاشية.mp3, 037  RTL_الصافات.mp3 and timings-001.json.

    The archive's Arabic names may be displayed as CP437 mojibake by ZIP tools;
    the leading ASCII digits remain unchanged and are all we need.
    """
    basename = filename.replace('\\', '/').rsplit('/', 1)[-1]
    if not basename.lower().endswith(suffix):
        return None
    stem = normalize_digits(basename[:-len(suffix)]).lstrip('\ufeff\u200e\u200f\u061c').strip()

    # Never extract the first three digits from a longer number.
    patterns = (
        r'^0*([0-9]{1,3})(?![0-9])',
        r'^(?:surah|sura|سورة|سوره)[\s._\-–]*0*([0-9]{1,3})(?![0-9])',
        r'^(?:timings?|ayahs?|verses?)[\s._\-–]*0*([0-9]{1,3})(?![0-9])',
    )
    for pattern in patterns:
        match = re.match(pattern, stem, flags=re.IGNORECASE)
        if match:
            number = int(match.group(1))
            return number if 1 <= number <= 114 else None
    return None


def is_macos_metadata(filename: str) -> bool:
    parts = filename.replace('\\', '/').split('/')
    return '__MACOSX' in parts or parts[-1].startswith('._') or parts[-1] == '.DS_Store'


def map_members(archive: zipfile.ZipFile, suffix: str, expected: int,
                canonical_folder=None):
    """Choose ONE authoritative directory (when provided), rejecting actual duplicates.

    The original timing ZIP holds historical alternatives in
    history/original-repeat-candidates/ alongside the intended
    mp3quran-format/ timing files. Those are NOT interchangeable.
    Canonical timing files are selected by their directory path,
    not by their order in the ZIP. Other folders are never mixed in.
    """
    mapped = {}
    unknown = []
    skipped_metadata = 0
    skipped_other_directories = 0
    for member in archive.infolist():
        if member.is_dir() or not member.filename.lower().endswith(suffix):
            continue
        if is_macos_metadata(member.filename):
            skipped_metadata += 1
            continue
        path_parts = member.filename.replace('\\', '/').split('/')
        directory_parts = [part.casefold() for part in path_parts[:-1]]
        if canonical_folder is not None and canonical_folder.casefold() not in directory_parts:
            skipped_other_directories += 1
            continue
        number = surah_number(member.filename, suffix)
        if number is None:
            unknown.append(member.filename)
            continue
        if number in mapped:
            raise ValueError(
                f'Duplicate surah {number:03d} within the selected {suffix} files: '
