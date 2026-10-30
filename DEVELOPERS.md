# للمطورين | Developer API

> **مشاري العفاسي — مصحف مجمع** | Mishary Alafasy — Collected Mushaf  
> رواية حفص عن عاصم • 114 سورة • ملف صوت MP3 لكل سورة • توقيتات JSON لكل آية

[🇸🇦 الدليل العربي](developers/README.md) · [English guide](developers/README.en.md) · [صيغة الملفات والروابط](developers/API.md) · [الحقوق والمصادر](developers/RIGHTS_AND_SOURCES.md)

## استخدام سريع / Quick start

هذا **كتالوج روابط ملفات ثابتة منشورة في GitHub Releases** وليس خدمة API تتطلب مفتاحًا أو حسابًا.

**Static, public release assets, not a hosted REST API.** No API key for public downloads.

- الإصدار: <https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/tag/v1.0.0>
- صوت سورة الفاتحة (النمط): `https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0/001.mp3`
- توقيت الفاتحة (النمط): `https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0/timings-001.json`

```js
const base = 'https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0';
function surahAssets(surah) {
  if (!Number.isInteger(surah) || surah < 1 || surah > 114) throw new RangeError('Surah must be 1..114');
  const n = String(surah).padStart(3, '0');
  return { audio: `${base}/${n}.mp3`, timings: `${base}/timings-${n}.json` };
}
```

> ⚠️ **حقوق النشر:** نشر الملفات في مستودع عام لا يمنح تلقائيًا إذنًا بإعادة النشر أو الاستعمال التجاري. راجع [الحقوق والمصادر](developers/RIGHTS_AND_SOURCES.md) واحصل على الأذونات المناسبة قبل تضمين التسجيلات في تطبيقات أخرى. **أفاد ناشر المستودع بأن الملفات مجانية الوصول والتنزيل؛ ولم تُثبت هنا رخصة لإعادة التوزيع أو الاستغلال التجاري.**
>
> ⚠️ **التحقق:** لم نتمكن من تجربة رابط تنزيل كل ملف مباشرة من بيئة إعداد هذا الدليل. يوجد [فحص آلي](developers/scripts/check_release.py) يفحص أسماء الأصول وملفات توقيتات مختارة عبر GitHub API بعد الرفع. راجع حالة الفحص قبل الاعتماد على الروابط في الإنتاج.

## أمثلة جاهزة

| المنصة | المثال | المطلوب |
|---|---|---|
| Next.js 15/16 (App Router) | [مثال الويب](developers/examples/nextjs/README.md) | React + مسار Proxy لتوقيتات JSON |
| Flutter | [مثال Flutter](developers/examples/flutter/README.md) | حزم `just_audio`, `http` |
| Android (Kotlin) | [مثال Android](developers/examples/android/README.md) | Android Studio + INTERNET |
| iOS (SwiftUI) | [مثال iOS](developers/examples/ios/README.md) | Xcode + AVFoundation |

**ملاحظة:** الأمثلة تعرض تشغيل سورة وتوقيتها وإظهار رقم الآية أثناء التشغيل. لا تتضمن نص المصحف؛ على تطبيقك تزويد نص صحيح برواية حفص وربط أرقام الآيات بنفس ترتيب السورة.

## فحص سلامة إصدار v1.0.0

```bash
python3 developers/scripts/check_release.py --sample-json
```

يفحص وجود `001.mp3 … 114.mp3` و`timings-001.json … timings-114.json` في أصول الإصدار، ثم بنية توقيتات ثلاث سور مختارة. يحتاج اتصالًا بالإنترنت؛ ولا يثبت دقة التزامن سمعيًا.

## ترخيص الأمثلة البرمجية

الكود التوضيحي الجديد، دون التسجيلات أو ملفات التوقيتات، موضح تحت [ترخيص MIT للأمثلة](developers/CODE-LICENSE.md). ولا يشمل الترخيص أيًا من أصول الصوت أو نص المصحف.
