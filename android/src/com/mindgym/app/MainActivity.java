package com.mindgym.app;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.View;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.Locale;

public class MainActivity extends Activity {
    private WebView web;
    private TextToSpeech tts;
    private volatile boolean ttsReady = false;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Window w = getWindow();
        boolean night = (getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK)
                == android.content.res.Configuration.UI_MODE_NIGHT_YES;
        int bg = night ? Color.rgb(20, 17, 42) : Color.rgb(244, 242, 251);
        w.setStatusBarColor(bg);
        w.setNavigationBarColor(bg);
        w.getDecorView().setBackgroundColor(bg);
        if (!night) {
            int flags = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            if (android.os.Build.VERSION.SDK_INT >= 26) flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
            w.getDecorView().setSystemUiVisibility(flags);
        }

        web = new WebView(this);
        web.setBackgroundColor(bg);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient());
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.addJavascriptInterface(new Bridge(), "AndroidTTS");
        web.addJavascriptInterface(new AppBridge(), "AndroidApp");
        setContentView(web);
        ReminderReceiver.schedule(this);

        tts = new TextToSpeech(this, new TextToSpeech.OnInitListener() {
            @Override
            public void onInit(int status) {
                if (status == TextToSpeech.SUCCESS) {
                    tts.setLanguage(Locale.US);
                    tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                        @Override public void onStart(String id) {}
                        @Override public void onDone(String id) { done(id); }
                        @Override public void onError(String id) { done(id); }
                    });
                    ttsReady = true;
                }
            }
        });

        String html = readAsset("index.html").replace("<html lang=\"en\">",
                "<html lang=\"en\" data-theme=\"" + (night ? "dark" : "light") + "\">");
        web.loadDataWithBaseURL("https://mindgym.app/", html, "text/html", "utf-8", null);
    }

    /** Daily reminder settings, called from the page. */
    public class AppBridge {
        @JavascriptInterface
        public String getReminder() {
            android.content.SharedPreferences p = ReminderReceiver.prefs(MainActivity.this);
            return (p.getBoolean("on", false) ? "1" : "0") + "," + p.getInt("h", 19) + "," + p.getInt("m", 0);
        }

        @JavascriptInterface
        public void setReminder(boolean on, int h, int m) {
            ReminderReceiver.prefs(MainActivity.this).edit().putBoolean("on", on).putInt("h", h).putInt("m", m).apply();
            ReminderReceiver.schedule(MainActivity.this);
            if (on && android.os.Build.VERSION.SDK_INT >= 33 && !notificationsAllowed()) {
                runOnUiThread(new Runnable() {
                    @Override public void run() {
                        requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 7);
                    }
                });
            }
        }

        @JavascriptInterface
        public boolean notificationsAllowed() {
            if (android.os.Build.VERSION.SDK_INT >= 33)
                return checkSelfPermission("android.permission.POST_NOTIFICATIONS") == android.content.pm.PackageManager.PERMISSION_GRANTED;
            return true;
        }

        @JavascriptInterface
        public void markWorkoutDone(String date) {
            ReminderReceiver.prefs(MainActivity.this).edit().putString("lastWorkout", date).apply();
        }
    }

    private void done(final String id) {
        web.post(new Runnable() {
            @Override public void run() {
                web.evaluateJavascript("window.__ttsDone&&window.__ttsDone(" + JSONQuote(id) + ")", null);
            }
        });
    }

    private static String JSONQuote(String s) {
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'";
    }

    private String readAsset(String name) {
        try {
            InputStream in = getAssets().open(name);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            in.close();
            return out.toString("UTF-8");
        } catch (Exception e) {
            return "<p>Could not load the app: " + e + "</p>";
        }
    }

    public class Bridge {
        @JavascriptInterface
        public boolean ready() { return ttsReady; }

        @JavascriptInterface
        public void speak(String text, float rate, String id) {
            if (!ttsReady) { done(id); return; }
            tts.setSpeechRate(rate);
            Bundle params = new Bundle();
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, params, id);
        }

        @JavascriptInterface
        public void stop() { if (ttsReady) tts.stop(); }
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("window.__back?window.__back():false", new android.webkit.ValueCallback<String>() {
            @Override public void onReceiveValue(String value) {
                if (!"true".equals(value)) finish();
            }
        });
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (ttsReady) tts.stop();
    }

    @Override
    protected void onDestroy() {
        if (tts != null) tts.shutdown();
        web.destroy();
        super.onDestroy();
    }
}
