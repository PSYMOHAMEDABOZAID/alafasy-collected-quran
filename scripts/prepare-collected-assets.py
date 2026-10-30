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
"""Split the ORIGINAL released ZIPs into 114 streamable MP3s and matched JSON files.

No interpolation/forced alignment or swapping in other recordings: timing values
are taken only from the accompanying v1.0.0 timing archive. On unexpected data,
FAIL before any release upload. This is a packaging/structural check, not an
independent auditory verification of each spoken verse boundary.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def numbered(stem):
    # Fail closed: number must be leading or prefixed by explicit 'surah' label.
    latin = stem.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'))
    for pattern in (r'^0*(\d{1,3})(?=$|[\s._\-–])',
                    r'^(?:surah|sura|سورة)[\s_\-–]*0*(\d{1,3})(?=$|[\s._\-–])'):
        match = re.search(pattern, latin, re.I)
        if match:
            number = int(match.group(1))
            if 1 <= number <= 114:
                return number
    return None


def numbered_members(archive, suffix, expected):
    mapped = {}
    ignored = []
    for entry in archive.infolist():
        if entry.is_dir() or not entry.filename.lower().endswith(suffix):
            continue
        name = Path(entry.filename).stem
        number = numbered(name)
        if number is None:
            ignored.append(entry.filename)
            continue
        if number in mapped:
            raise ValueError(f'Duplicate surah {number}: {entry.filename} and {mapped[number].filename}')
        mapped[number] = entry
    needed = set(range(1, expected + 1))
    missing = sorted(needed - set(mapped))
    extras = sorted(set(mapped) - needed)
    if missing or extras:
        raise ValueError(f'{suffix} ZIP mismatches: missing={missing}, extras={extras}; unrecognized={ignored[:15]}')
    print(f'Found {len(mapped)} distinct {suffix} files.')
    return mapped


def unit_multiplier(payload):
    if isinstance(payload, dict):
        unit = str(payload.get('time_unit') or payload.get('unit') or 'ms').strip().lower()
    else:
        unit = 'ms'
    if unit in ('ms', 'millisecond', 'milliseconds', 'msec'):
        return 1
    if unit in ('s', 'sec', 'second', 'seconds'):
        return 1000
    raise ValueError(f'Unsupported timing unit {unit!r}; will not guess.')


def parse_rows(payload, surah):
    multiplier = unit_multiplier(payload)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        declared = payload.get('surah')
        if declared is not None and int(declared) != surah:
            raise ValueError(f'Timing JSON declares surah {declared}, expected {surah}')
        rows = next((payload.get(key) for key in ('ayahs', 'ayat_timing', 'timings', 'data')
                     if isinstance(payload.get(key), list)), None)
    else:
        rows = None
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'Surah {surah}: timing JSON has no recognized verse array')
    result = []
    prev_start = -1
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f'Surah {surah}: invalid row {index}')
        ayah = row.get('ayah', row.get('number', row.get('verse')))
        start = row.get('start_time', row.get('start'))
        end = row.get('end_time', row.get('end'))
        if ayah is None or start is None or end is None:
            raise ValueError(f'Surah {surah}: missing ayah/start/end on row {index}')
        try:
            ayah_num, start_ms, end_ms = int(ayah), float(start) * multiplier, float(end) * multiplier
        except (ValueError, TypeError):
            raise ValueError(f'Surah {surah}: non-numeric timing on row {index}') from None
        if ayah_num != index or not (math.isfinite(start_ms) and math.isfinite(end_ms)) or \
