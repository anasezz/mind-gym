package com.mindgym.app;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

/** Shows the daily workout reminder and keeps the daily alarm scheduled (also after a reboot). */
public class ReminderReceiver extends BroadcastReceiver {
    static final String PREFS = "mindgym";
    static final String ACTION = "com.mindgym.app.REMIND";
    static final String CHANNEL = "daily_reminder";
    static final int SMALL_ICON = 0x7f010001; // res/drawable/ic_stat.png (see build.py)
    static final int FLAG_IMMUTABLE = 0x04000000;

    static SharedPreferences prefs(Context c) { return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE); }

    static String today() { return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date()); }

    static void schedule(Context c) {
        SharedPreferences p = prefs(c);
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        Intent i = new Intent(c, ReminderReceiver.class).setAction(ACTION);
        PendingIntent pi = PendingIntent.getBroadcast(c, 1, i, PendingIntent.FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE);
        am.cancel(pi);
        if (!p.getBoolean("on", false)) return;
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, p.getInt("h", 19));
        cal.set(Calendar.MINUTE, p.getInt("m", 0));
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() <= System.currentTimeMillis()) cal.add(Calendar.DAY_OF_YEAR, 1);
        am.setInexactRepeating(AlarmManager.RTC_WAKEUP, cal.getTimeInMillis(), AlarmManager.INTERVAL_DAY, pi);
    }

    @Override
    public void onReceive(Context c, Intent intent) {
        String a = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(a) || "android.intent.action.MY_PACKAGE_REPLACED".equals(a)) {
            schedule(c);
            return;
        }
        SharedPreferences p = prefs(c);
        if (!p.getBoolean("on", false)) return;
        if (today().equals(p.getString("lastWorkout", ""))) return; // already trained today

        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Daily workout reminder", NotificationManager.IMPORTANCE_DEFAULT);
            ch.setDescription("One reminder a day to do your Mind Gym workout");
            nm.createNotificationChannel(ch);
            b = new Notification.Builder(c, CHANNEL);
        } else {
            b = new Notification.Builder(c);
        }
        Intent open = new Intent(c, MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(c, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE);
        b.setSmallIcon(SMALL_ICON)
         .setContentTitle("Time for today's workout")
         .setContentText("5 exercises picked for your weak spots · about 15 minutes")
         .setContentIntent(pi)
         .setAutoCancel(true);
        nm.notify(1, b.build());
    }
}
