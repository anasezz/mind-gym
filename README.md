# Mind Gym

29 brain-training exercises in six areas (Attention, Brain Speed, Memory, People Skills, Intelligence, Navigation), packaged as an Android app.

## Install on Android

Download **[MindGym.apk](https://github.com/anasezz/mind-gym/releases/latest/download/MindGym.apk)** on your phone, open it, and allow installs from your browser or Files app when asked. Needs Android 7.0 or newer.

## What's here

- `index.html`: the whole app (all 29 exercises). It also runs in a browser.
- `android/`: a thin WebView wrapper with a bridge to the phone's text-to-speech, plus `build.py`, which builds and signs the APK without the Android SDK.

## Build

```bash
python3 android/build.py <tools_dir> MindGym.apk
```

`<tools_dir>` must contain `android-all.jar` (org.robolectric:android-all), `dx.jar` (com.jakewharton.android.repackaged:dalvik-dx) and `apksig.jar` (com.android.tools.build:apksig), all from Maven Central. Needs a JDK and Pillow. The signing key `android/mindgym-release.p12` is kept out of this repository; updates must be signed with the same key.
