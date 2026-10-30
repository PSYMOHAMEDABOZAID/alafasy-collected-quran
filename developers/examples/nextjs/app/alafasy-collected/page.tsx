'use client';

import { useEffect, useRef, useState } from 'react';

type Timing = { ayah: number; start_time: number; end_time: number };
const RELEASE = 'https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0';

export default function CollectedAlafasyDemo() {
  const player = useRef<HTMLAudioElement>(null);
  const [surah, setSurah] = useState(1);
  const [timings, setTimings] = useState<Timing[]>([]);
  const [ayah, setAyah] = useState<number | null>(null);
  const [status, setStatus] = useState('تحميل التوقيتات...');
  const code = String(surah).padStart(3, '0');
  const audioUrl = `/api/alafasy-collected/audio/${surah}`;
  const directAudioUrl = `${RELEASE}/${code}.mp3`;

  useEffect(() => {
    const controller = new AbortController();
    setTimings([]);
    setAyah(null);
    setStatus('تحميل التوقيتات...');
    fetch(`/api/alafasy-collected/timings/${surah}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<Timing[]>;
      })
      .then((rows) => {
        if (!controller.signal.aborted) {
          setTimings(rows);
          setStatus('التوقيتات جاهزة');
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setStatus(`تعذّر تحميل التوقيتات: ${String(error)}`);
      });
    return () => controller.abort();
  }, [surah]);

  function syncAyah() {
    const milliseconds = (player.current?.currentTime ?? 0) * 1000;
    const current = timings.find(
      (entry) => milliseconds >= entry.start_time && milliseconds < entry.end_time,
    );
    setAyah(current?.ayah ?? null);
  }

  return (
    <main dir="rtl" style={{ maxWidth: 680, margin: '3rem auto', padding: 16 }}>
      <h1>مشاري العفاسي — مصحف مجمع</h1>
      <p>المثال يعرض رقم الآية المتزامنة فقط؛ نص القرآن غير مضمّن.</p>
      <label htmlFor="surah">رقم السورة (1–114): </label>
      <input id="surah" type="number" min={1} max={114} value={surah}
        onChange={(e) => {
          const value = Number(e.target.value);
          if (Number.isInteger(value) && value >= 1 && value <= 114) setSurah(value);
        }}
      />
      <audio key={audioUrl} ref={player} controls preload="none" src={audioUrl}
        onTimeUpdate={syncAyah} onSeeked={syncAyah}
        onError={() => setStatus('تعذّر تشغيل ملف MP3؛ تحقق من رابط الإصدار')}
        style={{ display: 'block', width: '100%', marginTop: 20 }} />
      <p role="status">{status}</p>
      <h2 aria-live="polite">{ayah === null ? 'لا توجد آية محددة الآن' : `الآية ${ayah}`}</h2>
      <p>عدد التوقيتات المحمّلة: {timings.length}</p>
      <a href={directAudioUrl} target="_blank" rel="noreferrer">فتح رابط MP3 الأصلي</a>
    </main>
  );
}
