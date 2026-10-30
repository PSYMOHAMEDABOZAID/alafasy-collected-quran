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

VERSION = 'SOURCE_VERIFIED_V6_2026_10_31'
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
                f'{mapped[number].filename!r} and {member.filename!r}'
            )
        mapped[number] = member

    required = set(range(1, expected + 1))
    missing = sorted(required - mapped.keys())
    outside_range = sorted(mapped.keys() - required)
    if missing or outside_range or unknown:
        selected = f'folder {canonical_folder!r}' if canonical_folder else 'full archive'
        raise ValueError(
            f'{suffix} selection ({selected}) incomplete/invalid: '
            f'missing={missing}, unexpected_numbers={outside_range}, '
            f'unrecognized_count={len(unknown)}, examples={unknown[:8]}. '
            f'Ignored {skipped_other_directories} noncanonical files. '
            f'The script will NOT fall back to history/original-repeat-candidates.'
        )
    print(
        f'OK: {len(mapped)} {suffix} files from '
        f'{canonical_folder or "audio archive"}; '
        f'skipped {skipped_metadata} macOS entries and '
        f'{skipped_other_directories} other-directory files',
        flush=True,
    )
    return mapped


def timing_scale(payload) -> int:
    unit = ('ms' if not isinstance(payload, dict) else
            str(payload.get('time_unit') or payload.get('unit') or 'ms').lower().strip())
    if unit in {'ms', 'millisecond', 'milliseconds', 'msec'}:
        return 1
    if unit in {'s', 'sec', 'second', 'seconds'}:
        return 1000
    raise ValueError(f'Unknown timing unit {unit!r}; refusing to guess')


def normalize_timing_rows(payload, surah: int):
    scale = timing_scale(payload)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        declared = payload.get('surah')
        if declared is not None and int(declared) != surah:
            raise ValueError(f'Surah {surah}: JSON declares a different surah: {declared}')
        rows = next((payload[key] for key in ('ayahs', 'ayat_timing', 'timings', 'data', 'verse_timings')
                     if isinstance(payload.get(key), list)), None)
    else:
        rows = None
    if not rows or not isinstance(rows, list):
        raise ValueError(f'Surah {surah}: expected nonempty ayah timing list')

    result = []
    previous_start = -1
    # MP3Quran data may have a leading ayah=0 (the introductory basmalah);
    # it is not a Quran verse, so do not include it in the 6236 ayah count.
    if rows and isinstance(rows[0], dict) and str(rows[0].get('ayah', rows[0].get('aya', ''))) == '0':
        rows = rows[1:]
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Surah {surah}, row {index}: expected JSON object')
        ayah = row.get('ayah', row.get('aya', row.get('number', row.get('verse'))))
        start = row.get('start_time', row.get('start'))
        end = row.get('end_time', row.get('end'))
        if ayah is None or start is None or end is None:
            raise ValueError(f'Surah {surah}, row {index}: missing ayah/start/end')
        try:
            ayah = int(ayah)
            start_ms = float(start) * scale
            end_ms = float(end) * scale
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Surah {surah}, row {index}: invalid number') from exc
        if (ayah != index or not math.isfinite(start_ms) or not math.isfinite(end_ms)
                or start_ms < 0 or start_ms < previous_start or end_ms <= start_ms):
            raise ValueError(f'Surah {surah}, ayah {index}: timings not sequential/positive')
        result.append({'ayah': index, 'start_time': round(start_ms), 'end_time': round(end_ms)})
        previous_start = start_ms
    return result


def duration_seconds(mp3_path: Path) -> float:
    res = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(mp3_path)],
        capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        raise ValueError(f'{mp3_path.name}: ffprobe failed: {res.stderr[:200]}')
    try:
        duration = float(res.stdout.strip())
    except ValueError as exc:
        raise ValueError(f'{mp3_path.name}: no readable MP3 duration') from exc
    if not math.isfinite(duration) or duration <= 1:
        raise ValueError(f'{mp3_path.name}: bad audio duration {duration}')
    return duration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--timings', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected', type=int, default=114)
    args = parser.parse_args()
    if not 1 <= args.expected <= 114:
        parser.error('--expected must be 1..114')

    print(f'PREPARER_VERSION={VERSION}', flush=True)
    audio_dir = args.out / 'audio'
    timing_dir = args.out / 'timings'
    audio_dir.mkdir(parents=True, exist_ok=True)
    timing_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    total_ayahs = 0

    with zipfile.ZipFile(args.audio) as a, zipfile.ZipFile(args.timings) as t:
        mp3 = map_members(a, '.mp3', args.expected)
        js = map_members(t, '.json', args.expected, canonical_folder='mp3quran-format')
        for surah in range(1, args.expected + 1):
            n = f'{surah:03d}'
            destination = audio_dir / f'{n}.mp3'
            with a.open(mp3[surah]) as incoming, destination.open('wb') as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            if destination.stat().st_size < 10000:
                raise ValueError(f'{n}.mp3 appears truncated (<10KB)')

            with t.open(js[surah]) as raw:
                data = json.load(raw)
            ayahs = normalize_timing_rows(data, surah)
            duration = duration_seconds(destination)
            last_end = ayahs[-1]['end_time'] / 1000.0
            if last_end > duration + 3:
                raise ValueError(
                    f'Surah {n}: timing goes to {last_end:.2f}s '
                    f'but the original MP3 duration is {duration:.2f}s'
                )
            (timing_dir / f'timings-{n}.json').write_text(
                json.dumps(ayahs, ensure_ascii=False, separators=(',', ':')), encoding='utf-8'
            )
            total_ayahs += len(ayahs)
            manifest.append({
                'surah': surah, 'ayahs': len(ayahs),
                'seconds': round(duration, 3),
                'last_timing_seconds': round(last_end, 3),
                'bytes': destination.stat().st_size,
            })
            print(f'Surah {n}: {len(ayahs)} ayahs, {duration:.1f}s MP3, {last_end:.1f}s timing', flush=True)

    if args.expected == 114 and total_ayahs != EXPECTED_AYAH_TOTAL:
        raise ValueError(f'Timing rows total {total_ayahs}, expected {EXPECTED_AYAH_TOTAL}')
    (args.out / 'collected-manifest.json').write_text(
        json.dumps({
            'recording': 'Mishary Alafasy - collected Quran',
            'source_release': 'v1.0.0',
            'preparer_version': VERSION,
            'source_audio_archive': args.audio.name,
            'source_timing_archive': args.timings.name,
            'total_ayahs': total_ayahs,
            'surahs': manifest,
            'note': 'Validation of file structure/duration, not independent auditory verification of verse alignment',
        }, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'PASS {VERSION}: {args.expected} MP3 and timing files, {total_ayahs} verses', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'FAILED [{VERSION}] — nothing should be uploaded: {error}', file=sys.stderr)
        sys.exit(1)
