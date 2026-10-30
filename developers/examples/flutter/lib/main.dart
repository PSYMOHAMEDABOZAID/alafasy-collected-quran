import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';

const release = 'https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0';
String number(int surah) => surah.toString().padLeft(3, '0');

class VerseTiming {
  final int ayah;
  final int start;
  final int end;
  const VerseTiming(this.ayah, this.start, this.end);

  static List<VerseTiming> parse(String body) {
    final decoded = jsonDecode(body);
    if (decoded is! List || decoded.isEmpty || decoded.length > 286) {
      throw const FormatException('Unexpected timings array');
    }
    final result = <VerseTiming>[];
    for (final item in decoded) {
      if (item is! Map<String, dynamic>) throw const FormatException('Invalid timing row');
      final ayah = item['ayah'], start = item['start_time'], end = item['end_time'];
      if (ayah is! int || start is! num || end is! num ||
          ayah != result.length + 1 || start < 0 || end <= start ||
          (result.isNotEmpty && start < result.last.start)) {
        throw const FormatException('Invalid timings');
      }
      result.add(VerseTiming(ayah, start.round(), end.round()));
    }
    return result;
  }
}

void main() => runApp(const MaterialApp(home: AlafasyDemo()));

class AlafasyDemo extends StatefulWidget {
  const AlafasyDemo({super.key});
  @override
  State<AlafasyDemo> createState() => _AlafasyDemoState();
}

class _AlafasyDemoState extends State<AlafasyDemo> {
  final AudioPlayer player = AudioPlayer();
  StreamSubscription<Duration>? positionSubscription;
  int surah = 1;
  int? currentAyah;
  List<VerseTiming> timings = [];
  String status = 'اختر سورة ثم اضغط تشغيل';
  bool loading = false;
  int generation = 0;

  @override
  void initState() {
    super.initState();
    positionSubscription = player.positionStream.listen((position) {
      final ms = position.inMilliseconds;
      int? next;
      for (final row in timings) {
        if (row.start <= ms && ms < row.end) { next = row.ayah; break; }
      }
      if (mounted && currentAyah != next) setState(() => currentAyah = next);
    });
  }

  Future<void> loadAndPlay() async {
    final requestId = ++generation;
    setState(() { loading = true; status = 'تحميل التوقيتات والصوت...'; currentAyah = null; timings = []; });
    try {
      await player.stop();
      final response = await http.get(Uri.parse('$release/timings-${number(surah)}.json'))
          .timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) throw Exception('JSON HTTP ${response.statusCode}');
      final rows = VerseTiming.parse(utf8.decode(response.bodyBytes));
      if (!mounted || requestId != generation) return;
      timings = rows;
      await player.setUrl('$release/${number(surah)}.mp3');
      if (!mounted || requestId != generation) return;
      setState(() { loading = false; status = 'جاهز للتشغيل'; });
      await player.play();
    } catch (error) {
      if (mounted && requestId == generation) {
        setState(() { loading = false; status = 'تعذّر التشغيل: $error'; });
      }
    }
  }

  @override
  void dispose() {
    generation++;
    positionSubscription?.cancel();
    player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('مشاري العفاسي — مصحف مجمع')),
    body: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('رقم السورة (1–114) — رقم الآية فقط، دون نص المصحف'),
        DropdownButton<int>(
          value: surah,
          items: List.generate(114, (i) => DropdownMenuItem(value: i + 1, child: Text('سورة ${i + 1}'))),
          onChanged: loading ? null : (n) async {
            if (n == null) return;
            generation++;
            await player.stop();
            if (mounted) setState(() { surah = n; currentAyah = null; timings = []; status = 'اضغط تشغيل'; });
          },
        ),
        FilledButton(onPressed: loading ? null : loadAndPlay, child: const Text('تشغيل')),
        TextButton(onPressed: () => player.pause(), child: const Text('إيقاف مؤقت')),
        const SizedBox(height: 20),
        Text('الآية الحالية: ${currentAyah ?? "—"}', style: const TextStyle(fontSize: 26)),
        Text(status),
      ]),
    ),
  );
}
