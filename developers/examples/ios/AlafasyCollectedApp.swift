import SwiftUI
import AVFoundation

@main
struct AlafasyCollectedApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

struct VerseTiming: Decodable {
    let ayah: Int
    let start_time: Double
    let end_time: Double
}

@MainActor
final class RecitationPlayer: ObservableObject {
    @Published var surah: Int = 1
    @Published var currentAyah: Int?
    @Published var status = "اختر السورة ثم تشغيل"
    @Published var loading = false

    private let base = "https://github.com/PSYMOHAMEDABOZAID/alafasy-collected-quran/releases/download/v1.0.0"
    private var player: AVPlayer?
    private var observer: Any?
    private var timings: [VerseTiming] = []
    private var generation: Int = 0

    func loadAndPlay() async {
        generation += 1
        let requestId = generation
        stopPlayback()
        loading = true
        status = "تحميل التوقيتات..."
        currentAyah = nil
        timings = []
        let id = String(format: "%03d", surah)
        do {
            let (data, response) = try await URLSession.shared.data(
                from: URL(string: "\(base)/timings-\(id).json")!
            )
            guard (response as? HTTPURLResponse)?.statusCode == 200 else {
                throw NSError(domain: "Alafasy", code: 1, userInfo: [NSLocalizedDescriptionKey: "JSON HTTP error"])
            }
            guard data.count < 500_000 else { throw NSError(domain: "Alafasy", code: 2) }
            let parsed = try JSONDecoder().decode([VerseTiming].self, from: data)
            guard !parsed.isEmpty && parsed.count <= 286 && parsed.enumerated().allSatisfy({ index, row in
                row.ayah == index + 1 && row.start_time.isFinite && row.end_time.isFinite &&
                row.start_time >= 0 && row.end_time > row.start_time &&
                (index == 0 || row.start_time >= parsed[index - 1].start_time)
            }) else { throw NSError(domain: "Alafasy", code: 3, userInfo: [NSLocalizedDescriptionKey: "Invalid timings"] ) }
            guard requestId == generation else { return }
            timings = parsed
            let url = URL(string: "\(base)/\(id).mp3")!
            let item = AVPlayerItem(url: url)
            let audioPlayer = AVPlayer(playerItem: item)
            player = audioPlayer
            observer = audioPlayer.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.15, preferredTimescale: 600), queue: .main) { [weak self] time in
                guard let self else { return }
                let milliseconds = CMTimeGetSeconds(time) * 1000
                self.currentAyah = self.timings.first(where: {
                    $0.start_time <= milliseconds && milliseconds < $0.end_time
                })?.ayah
            }
            status = "التوقيتات جاهزة — جارٍ تشغيل الصوت"
            loading = false
            audioPlayer.play()
        } catch {
            guard requestId == generation else { return }
            status = "تعذّر التحميل: \(error.localizedDescription)"
            loading = false
        }
    }

    func togglePause() {
        guard let player else { return }
        if player.rate == 0 { player.play() } else { player.pause() }
    }

    func changeSurah(_ newValue: Int) {
        generation += 1
        stopPlayback()
        surah = newValue
        currentAyah = nil
        timings = []
        status = "اضغط تشغيل"
    }

    func stopPlayback() {
        if let observer, let player { player.removeTimeObserver(observer) }
        observer = nil
        player?.pause()
        player?.replaceCurrentItem(with: nil)
        player = nil
    }

}

struct ContentView: View {
    @StateObject private var model = RecitationPlayer()
    var body: some View {
        VStack(spacing: 20) {
            Text("مشاري العفاسي — مصحف مجمع").font(.title2).bold()
            Text("يعرض رقم الآية فقط — نص المصحف غير مضمّن")
            Picker("السورة", selection: Binding(
                get: { model.surah },
                set: { model.changeSurah($0) }
            )) {
                ForEach(1...114, id: \.self) { i in Text("سورة \(i)").tag(i) }
            }
            Button("تشغيل") { Task { await model.loadAndPlay() } }.disabled(model.loading)
            Button("إيقاف مؤقت / متابعة") { model.togglePause() }
            Text("الآية الحالية: \(model.currentAyah.map(String.init) ?? "—")").font(.title)
            Text(model.status).font(.footnote)
        }
        .padding()
        .onDisappear { model.stopPlayback() }
    }
}
