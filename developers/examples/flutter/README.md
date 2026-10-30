# Flutter (Android / iOS)

Run from a **new Flutter project** (Flutter 3.19+):

```bash
flutter create alafasy_collected_demo
cd alafasy_collected_demo
```

Replace `pubspec.yaml` and `lib/main.dart` with the files in this directory, then run:

```bash
flutter pub get
flutter run
```

**Android:** ensure `<uses-permission android:name="android.permission.INTERNET" />` is a direct child of `<manifest>` in `android/app/src/main/AndroidManifest.xml` (standard Flutter templates may already include it in debug but not release).

The demo uses `just_audio` and `http`, native audio position updates, and downloaded timing JSON. GitHub redirects, network blocks, and rate limiting can affect actual playback; test on real devices. Verse TEXT is not included. Check rights and source provenance before publishing a derivative app.
