# رابط الملفات | Static assets reference (v1.0.0)

هذا مستودع **أصول ملفات** وليس خادم REST API. لا يوجد endpoint رسمي مثل `GET /surahs` في هذا المشروع.

## Endpoints (file URL templates)

| النوع | القالب | مثال سورة 2 |
|---|---|---|
| Audio MP3 | `BASE/{NNN}.mp3` | `BASE/002.mp3` |
| Timings JSON | `BASE/timings-{NNN}.json` | `BASE/timings-002.json` |

`BASE=https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0`

The literal `BASE` in the table is shorthand, not an HTTP hostname. `NNN` is zero-padded 1–114. Do not use `latest` if you require immutable versioned links.

## Response structure

```ts
type VerseTiming = {
  ayah: number;        // starts at 1 for each surah
  start_time: number;  // milliseconds from beginning of the surah audio
  end_time: number;    // milliseconds, exclusive boundary
};
type Timings = VerseTiming[];
```

The producer's packaging script emits a JSON array for every surah. Sample (illustrative, not the actual recitation):

```json
[
  {"ayah": 1, "start_time": 1000, "end_time": 3500},
  {"ayah": 2, "start_time": 3500, "end_time": 6600}
]
```

Validate arrays, integer ayah indices, finite times and strictly positive durations before highlighting. Timing rows may have gaps; clear the highlight outside intervals. If the release is replaced, its URLs may change or fail.

## Error handling

- Missing or blocked URLs: handle `404`, `429`, network errors, redirects and GitHub asset removal.
- Browser CORS: use your server (or an approved CDN) for JSON retrieval; do **not** use a public CORS-bypass proxy or expose secret tokens in browser apps.
- Streaming: use the platform's native player and its actual clock. Do not estimate elapsed audio with a `setInterval` counter.
- Seek and playback speed: re-evaluate highlighting whenever the audio clock changes.
- Integrity: run [`check_release.py`](scripts/check_release.py) against the *actual* release. Its content checks are structural, not a human audio review.

## Asset naming check

Check for exactly `001.mp3` through `114.mp3` and `timings-001.json` through `timings-114.json`. Other release assets such as original ZIP archives or manifests may be present and are allowed.
