# Mind Gym

29 brain-training exercises in six areas (Attention, Brain Speed, Memory, People Skills, Intelligence, Navigation), packaged as an Android app. Each exercise has 9 levels (Beginner 1–3, Medium 4–6, Advanced 7–9); clear a level with 70% accuracy to unlock the next. A brain report shows your weakest areas and suggests what to play next.

## Install on Android

Download **[MindGym.apk](https://github.com/anasezz/mind-gym/raw/main/MindGym.apk)** on your phone, open it, and allow installs from your browser or Files app when asked. Needs Android 7.0 or newer.

## What's here

- `index.html`: the whole app (all 29 exercises). It also runs in a browser.
- `android/`: a thin WebView wrapper with a bridge to the phone's text-to-speech, plus `build.py`, which builds and signs the APK without the Android SDK.

## Build

```bash
python3 android/build.py <tools_dir> MindGym.apk
```

`<tools_dir>` must contain `android-all.jar` (org.robolectric:android-all), `dx.jar` (com.jakewharton.android.repackaged:dalvik-dx) and `apksig.jar` (com.android.tools.build:apksig), all from Maven Central. Needs a JDK and Pillow. The signing key `android/mindgym-release.p12` is kept out of this repository; updates must be signed with the same key.
