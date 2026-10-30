
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
    """Identify the surah number from its filename, without trusting its Arabic text.

    The real archive contains e.g. ``088الغاشيه.mp3`` and
    ``037  \u200f_الصافات.mp3``. The number is not always separated from
    the Arabic name by whitespace or underscore. ZIP's legacy filename encoding
    can also display Arabic as mojibake, but the ASCII numeric prefix survives.
    Never interpret a four-digit number as a shorter surah number.
    """
    latin = stem.translate(str.maketrans(
        '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789',
    ))
    latin = latin.lstrip('\ufeff\u200e\u200f\u061c').strip()

    for pattern in (
        r'^([0-9]{1,3})(?![0-9])',
        r'^(?:surah|sura|سورة)[\s._\-–]*([0-9]{1,3})(?![0-9])',
    ):
        match = re.match(pattern, latin, re.IGNORECASE)
        if match:
            number = int(match.group(1))
            if 1 <= number <= 114:
                return number
    return None


def numbered_members(archive, suffix, expected):
    mapped = {}
    ignored = []
    skipped_macos = 0

    for entry in archive.infolist():
        if entry.is_dir() or not entry.filename.lower().endswith(suffix):
            continue

        path_parts = entry.filename.replace('\\', '/').split('/')
        base_name = path_parts[-1]

        # Ignore macOS resource-fork metadata, not real MP3 files.
        if '__MACOSX' in path_parts or base_name.startswith('._'):
            skipped_macos += 1
            continue

        number = numbered(Path(base_name).stem)

        if number is None:
            ignored.append(entry.filename)
            continue

        if number in mapped:
            raise ValueError(
                f'Duplicate surah {number}: '
                f'{entry.filename} and {mapped[number].filename}'
            )

        mapped[number] = entry

    needed = set(range(1, expected + 1))
    missing = sorted(needed - set(mapped))
    extras = sorted(set(mapped) - needed)

    if missing or extras or ignored:
        raise ValueError(
            f'{suffix} ZIP mismatches: '
            f'missing={missing}, extras={extras}; '
            f'unrecognized real files={ignored[:20]} '
            f'(count={len(ignored)}); '
            f'ignored AppleDouble files={skipped_macos}'
        )

    print(
        f'Found {len(mapped)} distinct {suffix} files; '
        f'ignored {skipped_macos} harmless macOS metadata entries.',
        flush=True,
    )

    return mapped


def unit_multiplier(payload):
    if isinstance(payload, dict):
        unit = str(
            payload.get('time_unit')
            or payload.get('unit')
            or 'ms'
        ).strip().lower()
    else:
        unit = 'ms'

    if unit in ('ms', 'millisecond', 'milliseconds', 'msec'):
        return 1

    if unit in ('s', 'sec', 'second', 'seconds'):
        return 1000

    raise ValueError(
        f'Unsupported timing unit {unit!r}; will not guess.'
    )


def parse_rows(payload, surah):
    multiplier = unit_multiplier(payload)

    if isinstance(payload, list):
        rows = payload

    elif isinstance(payload, dict):
        declared = payload.get('surah')

        if declared is not None and int(declared) != surah:
            raise ValueError(
                f'Timing JSON declares surah {declared}, '
                f'expected {surah}'
            )

        rows = next(
            (
                payload.get(key)
                for key in (
                    'ayahs',
                    'ayat_timing',
                    'timings',
                    'data',
                )
                if isinstance(payload.get(key), list)
            ),
            None,
        )
    else:
        rows = None

    if not isinstance(rows, list) or not rows:
        raise ValueError(
            f'Surah {surah}: timing JSON has no recognized verse array'
        )

    result = []
    prev_start = -1

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(
                f'Surah {surah}: invalid row {index}'
            )

        ayah = row.get(
            'ayah',
            row.get('number', row.get('verse'))
        )

        start = row.get(
            'start_time',
            row.get('start')
        )

        end = row.get(
            'end_time',
            row.get('end')
        )

        if ayah is None or start is None or end is None:
            raise ValueError(
                f'Surah {surah}: '
                f'missing ayah/start/end on row {index}'
            )

        try:
            ayah_num = int(ayah)
            start_ms = float(start) * multiplier
            end_ms = float(end) * multiplier
        except (ValueError, TypeError):
            raise ValueError(
                f'Surah {surah}: non-numeric timing on row {index}'
            ) from None

        if (
            ayah_num != index
            or not (
                math.isfinite(start_ms)
                and math.isfinite(end_ms)
            )
            or start_ms < 0
            or start_ms < prev_start
            or end_ms <= start_ms
        ):
            raise ValueError(
                f'Surah {surah}: '
                f'invalid order or time at ayah {ayah_num}'
            )

        result.append({
            'ayah': ayah_num,
            'start_time': round(start_ms),
            'end_time': round(end_ms),
        })

        prev_start = start_ms

    return result


def duration_in_seconds(path):
    process = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    if process.returncode:
        raise RuntimeError(
            f'ffprobe failed on {path.name}: '
            f'{process.stderr[:250]}'
        )

    duration = float(process.stdout.strip())

    if not math.isfinite(duration) or duration < 1:
        raise ValueError(
            f'Invalid MP3 duration: {path.name}'
        )

    return duration


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--audio',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--timings',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--out',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--expected',
        type=int,
        default=114,
    )

    args = parser.parse_args()

    if not 1 <= args.expected <= 114:
        parser.error(
            '--expected must be in range 1..114'
        )

    audio_out = args.out / 'audio'
    timing_out = args.out / 'timings'

    audio_out.mkdir(
        parents=True,
        exist_ok=True,
    )

    timing_out.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_ayahs = 0
    manifest = []

    with (
        zipfile.ZipFile(args.audio) as audio_zip,
        zipfile.ZipFile(args.timings) as timing_zip,
    ):
        mp3s = numbered_members(
            audio_zip,
            '.mp3',
            args.expected,
        )

        jsons = numbered_members(
            timing_zip,
            '.json',
            args.expected,
        )

        for surah in range(1, args.expected + 1):
            key = f'{surah:03d}'

            audio_dest = audio_out / f'{key}.mp3'

            with (
                audio_zip.open(mp3s[surah]) as reader,
                audio_dest.open('wb') as writer,
            ):
                shutil.copyfileobj(
                    reader,
                    writer,
                    length=1024 * 1024,
                )

            if audio_dest.stat().st_size < 10000:
                raise ValueError(
                    f'Surah {surah}: suspiciously small audio'
                )

            with timing_zip.open(jsons[surah]) as reader:
                payload = json.load(reader)

            rows = parse_rows(
                payload,
                surah,
            )

            duration = duration_in_seconds(
                audio_dest
            )

            final_end = (
                rows[-1]['end_time'] / 1000
            )

            if final_end > duration + 3:
                raise ValueError(
                    f'Surah {surah}: '
                    f'timing ends at {final_end:.1f}s '
                    f'but audio lasts {duration:.1f}s'
                )

            timing_path = (
                timing_out / f'timings-{key}.json'
            )

            timing_path.write_text(
                json.dumps(
                    rows,
                    ensure_ascii=False,
                    separators=(',', ':'),
                ),
                encoding='utf-8',
            )

            total_ayahs += len(rows)

            manifest.append({
                'surah': surah,
                'ayahs': len(rows),
                'seconds': round(duration, 3),
                'last_timing_seconds': round(
                    final_end,
                    3,
                ),
                'bytes': audio_dest.stat().st_size,
            })

            print(
                f'{surah:03d}/{args.expected}: '
                f'{len(rows)} ayahs; '
                f'audio {duration:.1f}s; '
                f'last timing {final_end:.1f}s',
                flush=True,
            )

    if args.expected == 114 and total_ayahs != 6236:
        raise ValueError(
            f'All timing rows total {total_ayahs}, '
            f'expected 6236 for Hafs. '
            f'Refusing publish.'
        )

    manifest_path = (
        args.out / 'collected-manifest.json'
    )

    manifest_path.write_text(
        json.dumps(
            {
                'recording': 'Mishary Alafasy collected',
                'source_release': 'v1.0.0',
                'source_audio_archive': args.audio.name,
                'source_timing_archive': args.timings.name,
                'total_ayahs': total_ayahs,
                'surahs': manifest,
                'note': (
                    'Structure and duration checks only; '
                    'verse alignment is not aurally certified.'
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print(
        f'PASS: {args.expected} chapter audio files '
        f'and {total_ayahs} timing rows. '
        f'Ready for upload.',
        flush=True,
    )


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(
            f'FAILED — nothing should be uploaded: {exc}',
            file=sys.stderr,
        )
        sys.exit(1)
