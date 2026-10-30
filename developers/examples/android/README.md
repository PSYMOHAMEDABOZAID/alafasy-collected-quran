# Android (native Kotlin, Media3)

This is a **minimal Gradle source project**, using Android Gradle Plugin 8.5.2, Kotlin 2.0.20, Media3 1.4.1, Java 17, compileSdk 35.

- Open `developers/examples/android` in Android Studio, with Android SDK 35 and a compatible Gradle 8.7 installation. If the IDE requires a wrapper, create a new **Empty Views Activity** project and copy `app/src/main/` plus the dependencies from `app/build.gradle.kts` into it, or generate the wrapper using a local Gradle 8.7 installation (`gradle wrapper --gradle-version 8.7`). The ZIP does **not** include a Gradle binary or wrapper JAR.
- Build and run with Internet access. Choose surah 1–114 and press play; on a successful fetch the MP3 streams using Media3 and the ayah number updates on a 150ms display timer using the **player's** position, not a fabricated elapsed timer.
- No Quran text, audio, or JSON is bundled. Check copyright permissions for your intended distribution. This demo is not a production background-audio implementation.
