# Mishary Alafasy — Collected Mushaf: Developer guide

**Scope:** 114 per-surah MP3 files and JSON verse timing files, for Hafs recitation applications. The source release describes the collection as assembled from recordings whose dates are not documented and may differ by surah.

## This is a static download catalog, not a hosted API

Release: <https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/tag/v1.0.0>

```text
BASE = https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0
Audio for surah 2   = BASE/002.mp3
Timings for surah 2 = BASE/timings-002.json
```

For a surah integer 1–114, format the number with three digits; do not include the Arabic title in the filename. Downloading public release assets requires no repository API key; network access and availability are still required.

### Timing shape

`[{"ayah": 1, "start_time": 0, "end_time": 1200}, ...]` — **illustrative values, not actual ayah boundaries**. Times are milliseconds relative to the start of the corresponding MP3. Use `playbackSeconds * 1000` to find the current verse. Provide your own correctly licensed Hafs text for on-screen display.

### Cross-origin browser access

Direct JSON `fetch` requests can be blocked by CORS. The [Next.js example](examples/nextjs/README.md) includes a **server-side proxy route in your own application**; there is no public proxy hosted by this repository. A normal HTML audio element can often use the media URL without fetching the bytes in JavaScript.

### Examples

- [Next.js 15/16](examples/nextjs/README.md) · [Flutter](examples/flutter/README.md)
- [Android/Kotlin](examples/android/README.md) · [iOS/SwiftUI](examples/ios/README.md)

### Integrity and usage rights

Check release asset names and sample JSON with `python3 developers/scripts/check_release.py --sample-json` (also available as a GitHub Action). This is a structural check, **not independent verification of auditory verse alignment**. GitHub Releases is not a streaming CDN with a contractual uptime guarantee. Implement graceful failures and caching when permitted.

**The publisher says the files are free to access and download. Public access alone does not grant redistribution or commercial rights for the original recordings or third-party Quran text.** The owner's entitlement to grant redistribution or commercial rights has not been established here. See [Rights and source provenance](RIGHTS_AND_SOURCES.md). Contact relevant rights holders for permission where needed.

Example source code and the checker are separately offered under [MIT](CODE-LICENSE.md); this license does not cover audio or timing assets.
