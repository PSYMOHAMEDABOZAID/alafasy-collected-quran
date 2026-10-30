#!/usr/bin/env python3
"""Verify a public GitHub release contains 114 MP3 + 114 JSON timing assets.

Uses only Python stdlib; -— no GitHub tokens required for a public repository.
GITHUB_TOKEN can help with API rate limits. Does not verify auditory alignment.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

OWNER = 'PSYMOHAMEDABOZAID'
REPO = 'alafasy-collected-quran'
TAG = 'v1.0.0'
API = f'https://api.github.com/repos/{OWNER}/{REPO}'
EXPECTED = {f'{n:03d}.mp3' for n in range(1, 115)} | {
    f'timings-{n:03d}.json' for n in range(1, 115)
}
SAMPLES = {1: 7, 2: 286, 114: 6}


def read_json(url: str) -> Any:
    headers = {
        'User-Agent': 'alafasy-collected-developer-asset-checker/1.0',
        'Accept': 'application/vnd.github+json' if url.startswith(API) else 'application/json',
    }
    token = os.getenv('GITHUB_TOKEN')
    if token and url.startswith('https://api.github.com/'):
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError(f'JSON too large at {url}')
        return json.loads(raw.decode('utf-8-sig'))


def check_names(assets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    names: dict[str, dict[str, Any]] = {}
    for asset in assets:
        name = asset.get('name')
        if not isinstance(name, str):
            raise ValueError('Release asset with no name')
        if name in names:
            raise ValueError(f'Duplicate release asset: {name}')
        names[name] = asset
    missing = sorted(EXPECTED - names.keys())
    if missing:
        raise ValueError(f'Missing {len(missing)} audio/timing assets: {missing}')
    zeros = [name for name in EXPECTED if not isinstance(names[name].get('size'), int) or names[name]['size'] <= 0]
    if zeros:
        raise ValueError(f'Empty or unknown-size release assets: {sorted(zeros)}')
    print(f'PASS metadata: {len(assets)} release assets, 114 MP3 + 114 JSON present')
    return names


def validate_timings(rows: Any, surah: int, count: int | None = None) -> int:
    if not isinstance(rows, list) or not (1 <= len(rows) <= 286):
        raise ValueError(f'Surah {surah}: timings not a plausible nonempty array')
    if count is not None and len(rows) != count:
        raise ValueError(f'Surah {surah}: expected {count} verses, found {len(rows)}')
    previous_start = -1
    for index, item in enumerate(rows, 1):
        if not isinstance(item, dict) or item.get('ayah') != index:
            raise ValueError(f'Surah {surah}: invalid verse number at row {index}')
        start = item.get('start_time')
        end = item.get('end_time')
        if (isinstance(start, bool) or isinstance(end, bool) or
                not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or
                start != start or end != end or not (-float('inf') < start < float('inf')) or
                not (-float('inf') < end < float('inf')) or
                start < 0 or start < previous_start or end <= start):
            raise ValueError(f'Surah {surah}: bad timing at row {index}')
        previous_start = start
    return len(rows)


def fetch_assets(release_id: int) -> list[dict[str, Any]]:
    result = []
    for page in range(1, 30):
        chunk = read_json(f'{API}/releases/{release_id}/assets?per_page=100&page={page}')
        if not isinstance(chunk, list):
            raise ValueError('GitHub asset API did not return a list')
        result.extend(chunk)
        if len(chunk) < 100:
            return result
    raise ValueError('Too many asset pages: stopped at page 29')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    level = parser.add_mutually_exclusive_group()
    level.add_argument('--sample-json', action='store_true', help='Download/validate JSON for surahs 1, 2 and 114')
    level.add_argument('--all-json', action='store_true', help='Download/validate all 114 JSON assets (slow)')
    args = parser.parse_args()

    release = read_json(f'{API}/releases/tags/{TAG}')
    release_id = release.get('id')
    if not isinstance(release_id, int):
        raise ValueError('Release ID unavailable')
    assets = check_names(fetch_assets(release_id))
    targets = range(1, 115) if args.all_json else SAMPLES if args.sample_json else []
    total = 0
    for surah in targets:
        name = f'timings-{surah:03d}.json'
        url = assets[name].get('browser_download_url')
        if not isinstance(url, str) or not url.startswith('https://github.com/'):
            raise ValueError(f'Unexpected URL for {name}: {url}')
        total += validate_timings(read_json(url), surah, SAMPLES.get(surah))
        print(f'PASS {name}: valid JSON')
    print(f'PASS: {len(targets)} JSON files checked ({total} verse rows).')
    print('Note: this verifies asset presence and JSON structure, not that audio plays or verse boundaries match by ear.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f'FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
