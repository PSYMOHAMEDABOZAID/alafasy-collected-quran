161
162
163
164
165
166
167
168
169
170
171
172
173
174
175
176
177
178
179
180
181
182
183
184
185
186
187
188
189
190
191
192
193
194
195
196
197
198
199
200
201
202
203
204
205
206
207
208
209
210
211
212
213
214
215
216
217
218
219
220
221
222
223
224
225
226
227
228
229
230
231
232
233
234
235
236
237
238
239
240
241
242
243
244
245
246
247
248
249
250
251
252
253
254
255
256
257
258
259
260
261
262
263
264
265
266
267
268
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
