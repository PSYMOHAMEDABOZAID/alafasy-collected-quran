import { NextResponse } from 'next/server';

// Next.js 15/16 App Router: dynamic route params are asynchronous.
// This endpoint is part of YOUR application, not an API hosted by the audio repository.
const RELEASE = 'https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0';
type VerseTiming = { ayah: number; start_time: number; end_time: number };
type RouteContext = { params: Promise<{ surah: string }> };

function isTimingArray(value: unknown): value is VerseTiming[] {
  if (!Array.isArray(value) || value.length === 0 || value.length > 286) return false;
  let lastStart = -1;
  for (let index = 0; index < value.length; index++) {
    const row = value[index] as Record<string, unknown> | null;
    if (!row || typeof row !== 'object' || Array.isArray(row)) return false;
    if (row.ayah !== index + 1 || typeof row.start_time !== 'number' ||
        typeof row.end_time !== 'number' || !Number.isFinite(row.start_time) ||
        !Number.isFinite(row.end_time) || row.start_time < 0 ||
        row.start_time < lastStart || row.end_time <= row.start_time) return false;
    lastStart = row.start_time;
  }
  return true;
}

export async function GET(_request: Request, { params }: RouteContext) {
  const { surah } = await params;
  if (!/^\d{1,3}$/.test(surah) || Number(surah) < 1 || Number(surah) > 114) {
    return NextResponse.json({ error: 'Surah must be 1–114' }, { status: 400 });
  }
  const id = String(Number(surah)).padStart(3, '0');
  const url = `${RELEASE}/timings-${id}.json`;
  try {
    const response = await fetch(url, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      return NextResponse.json({ error: 'Timing source unavailable', upstreamStatus: response.status }, { status: 502 });
    }
    const size = response.headers.get('content-length');
    if (size && Number(size) > 500_000) {
      return NextResponse.json({ error: 'Unexpected timing size' }, { status: 502 });
    }
    const body = await response.text();
    if (body.length > 500_000) {
      return NextResponse.json({ error: 'Unexpected timing size' }, { status: 502 });
    }
    const value: unknown = JSON.parse(body);
    if (!isTimingArray(value)) {
      return NextResponse.json({ error: 'Unexpected timing data' }, { status: 502 });
    }
    return NextResponse.json(value, {
      headers: { 'Cache-Control': 'public, max-age=60, s-maxage=3600' },
    });
  } catch {
    return NextResponse.json({ error: 'Unable to load timing source' }, { status: 502 });
  }
}
