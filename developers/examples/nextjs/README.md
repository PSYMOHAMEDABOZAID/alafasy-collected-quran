# Next.js App Router example (15 / 16)

A standalone webpage with native HTML5 audio, surah selector, and ayah number highlight based on MP3 playback time. No Quran text is bundled.

1. From your Next.js App Router project, copy `app/alafasy-collected/page.tsx`, `app/api/alafasy-collected/timings/[surah]/route.ts`, and `app/api/alafasy-collected/audio/[surah]/route.ts` into the corresponding locations in your app.
2. Run `npm run build`, then visit `/alafasy-collected`.
3. Click play. The page loads JSON via **your application's server route** to avoid browser cross-origin JSON limitations.

Both API routes expect Next.js **15/16**, where `params` is a `Promise`. For **Next.js 14**, replace each `GET` handler context with `{ params }: {params:{surah:string}}` and remove `await` before `params`.

Release assets are static GitHub downloads. Audio media may be blocked by the network, removed, or redirect; use a licensed streaming CDN if production reliability is necessary. The code does not ship Quran verse text and cannot independently certify the audio timing boundaries.

The **audio relay** endpoint is optional but the example page uses it by default, to support HTTP Range requests over the same origin. For a small demonstration it can avoid browser access issues. **Do not deploy as an unrestricted production audio CDN on Vercel:** large MP3s, function time limits and bandwidth quotas may interrupt playback. For production, use an appropriately licensed dedicated audio origin and point the player at that host.
