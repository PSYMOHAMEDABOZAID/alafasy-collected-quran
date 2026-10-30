// Same-origin media relay for limited demonstration use, with Range support.
// For production prefer licensed CDN/object storage: Vercel functions have streaming,
// bandwidth and execution limits. GitHub Release URLs are not a media SLA.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const BASE = 'https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0';
type Context = { params: Promise<{ surah: string }> };

export async function GET(request: Request, { params }: Context): Promise<Response> {
  const { surah } = await params;
  if (!/^\d{1,3}$/.test(surah) || Number(surah) < 1 || Number(surah) > 114) {
    return new Response('Invalid surah', { status: 400 });
  }
  const id = String(Number(surah)).padStart(3, '0');
  const range = request.headers.get('range');
  if (range && !/^bytes=\d*-\d*$/.test(range)) {
    return new Response('Unsupported byte range', { status: 416 });
  }
  try {
    const headers: HeadersInit = { 'User-Agent': 'AlafasyCollectedDemo/1.0' };
    if (range) headers.Range = range;
    const upstream = await fetch(`${BASE}/${id}.mp3`, {
      redirect: 'follow',
      headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(90000),
    });
    if ((upstream.status !== 200 && upstream.status !== 206) || !upstream.body) {
      await upstream.body?.cancel();
      return new Response('Source audio unavailable', { status: 502 });
    }
    const responseHeaders = new Headers();
    responseHeaders.set('Content-Type', 'audio/mpeg');
    responseHeaders.set('Cache-Control', 'public, max-age=60');
    for (const header of ['content-range', 'accept-ranges', 'content-length']) {
      const value = upstream.headers.get(header);
      if (value) responseHeaders.set(header, value);
    }
    // Don't claim Range support if the origin didn't provide it.
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return new Response('Audio relay failed', { status: 502 });
  }
}
