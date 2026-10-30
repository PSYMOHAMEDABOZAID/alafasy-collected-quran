# iPhone/iPad — SwiftUI + AVFoundation

1. Open Xcode and create **iOS App**, interface **SwiftUI**, language **Swift** (iOS 16+).
2. Remove generated `App` entry file and replace it with `AlafasyCollectedApp.swift` from this folder. Remove the generated `ContentView.swift` (this file already declares `ContentView`). Keep exactly **one** `@main` App type.
3. Run on a device/simulator with access to GitHub. Pick a surah then press play.

Uses `URLSession` to obtain JSON and `AVPlayer` to stream audio, with the player clock driving ayah updates. GitHub may redirect, throttle or restrict access. This is a simple learning example (no background audio, no caching, no text). Check the rights document before using the recordings in a publicly distributed app.
