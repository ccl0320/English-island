package com.ccl0320.englishisland;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;

import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Checks the GitHub release "apk-latest" for a newer build and, if the grown-up agrees,
 * downloads it and opens Android's installer. The new APK is signed with the same key,
 * so it installs over this one and the child's progress is kept.
 * Silent when offline or when nothing is newer.
 */
public class Updater {
    static final String VERSION_URL =
            "https://github.com/ccl0320/english-island/releases/download/apk-latest/version.json";
    static final String DEFAULT_APK_URL =
            "https://github.com/ccl0320/english-island/releases/download/apk-latest/English-Island.apk";

    private final Activity act;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private File pendingApk;          // downloaded, waiting for "install unknown apps" permission
    private boolean busy = false;

    Updater(Activity act) {
        this.act = act;
    }

    /** Runs the check in the background; shows a dialog only when a newer version exists. */
    void check() {
        if (busy) return;
        busy = true;
        new Thread(() -> {
            try {
                JSONObject v = new JSONObject(new String(get(VERSION_URL + "?t=" + System.currentTimeMillis()), "UTF-8"));
                long latest = v.getLong("versionCode");
                String name = v.optString("versionName", String.valueOf(latest));
                String apk = v.optString("apk", DEFAULT_APK_URL);
                if (latest > currentCode()) {
                    ui.post(() -> offer(name, apk));
                    return;
                }
            } catch (Exception ignored) {
                // offline, or no version.json published yet: just play
            }
            busy = false;
        }).start();
    }

    /** Called from onResume: continue an install that was waiting for the permission screen. */
    void resume() {
        if (pendingApk != null && canInstall()) {
            File f = pendingApk;
            pendingApk = null;
            install(f);
        }
    }

    private long currentCode() throws Exception {
        PackageInfo p = act.getPackageManager().getPackageInfo(act.getPackageName(), 0);
        return Build.VERSION.SDK_INT >= 28 ? p.getLongVersionCode() : p.versionCode;
    }

    private String currentName() {
        try {
            return act.getPackageManager().getPackageInfo(act.getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }

    private void offer(String name, String apkUrl) {
        if (act.isFinishing()) { busy = false; return; }
        new AlertDialog.Builder(act)
                .setTitle("有新版本！New version")
                .setMessage("English Island " + name + " 已推出（目前 " + currentName() + "）。\n"
                        + "要現在更新嗎？遊戲進度會保留。\n\nUpdate now? Your progress is kept.")
                .setPositiveButton("更新 Update", (d, w) -> download(apkUrl))
                .setNegativeButton("稍後 Later", (d, w) -> busy = false)
                .setOnCancelListener(d -> busy = false)
                .show();
    }

    private void download(String apkUrl) {
        final AlertDialog progress = new AlertDialog.Builder(act)
                .setTitle("下載中… Downloading")
                .setMessage("0%")
                .setCancelable(false)
                .show();
        new Thread(() -> {
            File out = new File(act.getCacheDir(), "update/English-Island.apk");
            try {
                out.getParentFile().mkdirs();
                HttpURLConnection c = open(apkUrl);
                long total = c.getContentLengthLong();
                try (InputStream in = c.getInputStream(); OutputStream os = new FileOutputStream(out)) {
                    byte[] buf = new byte[64 * 1024];
                    long got = 0;
                    int n, lastPct = -1;
                    while ((n = in.read(buf)) > 0) {
                        os.write(buf, 0, n);
                        got += n;
                        if (total > 0) {
                            int pct = (int) (got * 100 / total);
                            if (pct != lastPct) {
                                lastPct = pct;
                                ui.post(() -> progress.setMessage(pct + "%"));
                            }
                        }
                    }
                } finally {
                    c.disconnect();
                }
                ui.post(() -> {
                    progress.dismiss();
                    busy = false;
                    install(out);
                });
            } catch (Exception e) {
                ui.post(() -> {
                    progress.dismiss();
                    busy = false;
                    new AlertDialog.Builder(act)
                            .setTitle("下載失敗 Download failed")
                            .setMessage("請確認網路後再開一次 App。\nPlease check the internet and open the app again.")
                            .setPositiveButton("OK", null)
                            .show();
                });
            }
        }).start();
    }

    private boolean canInstall() {
        return Build.VERSION.SDK_INT < 26 || act.getPackageManager().canRequestPackageInstalls();
    }

    private void install(File apk) {
        if (!canInstall()) {
            // Android 8+: the user must allow this app to install updates once.
            pendingApk = apk;
            new AlertDialog.Builder(act)
                    .setTitle("需要允許安裝")
                    .setMessage("下一頁請打開「允許來自這個來源的應用程式」，然後按返回鍵，就會開始安裝。\n\n"
                            + "Turn on \"Allow from this source\", then press Back.")
                    .setPositiveButton("OK", (d, w) -> act.startActivity(new Intent(
                            Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                            Uri.parse("package:" + act.getPackageName()))))
                    .setNegativeButton("稍後 Later", (d, w) -> pendingApk = null)
                    .show();
            return;
        }
        Uri uri = FileProvider.getUriForFile(act, act.getPackageName() + ".updates", apk);
        Intent i = new Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
        act.startActivity(i);
    }

    private static HttpURLConnection open(String url) throws Exception {
        // GitHub release downloads redirect (https -> https) to its file storage.
        for (int hops = 0; hops < 5; hops++) {
            HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(8000);
            c.setReadTimeout(20000);
            c.setInstanceFollowRedirects(false);
            c.setRequestProperty("User-Agent", "EnglishIsland-App");
            int code = c.getResponseCode();
            if (code >= 300 && code < 400) {
                String loc = c.getHeaderField("Location");
                c.disconnect();
                if (loc == null) break;
                url = new URL(new URL(url), loc).toString();
                continue;
            }
            if (code != 200) {
                c.disconnect();
                throw new Exception("HTTP " + code);
            }
            return c;
        }
        throw new Exception("too many redirects");
    }

    private static byte[] get(String url) throws Exception {
        HttpURLConnection c = open(url);
        try (InputStream in = c.getInputStream()) {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
            return b.toByteArray();
        } finally {
            c.disconnect();
        }
    }
}
