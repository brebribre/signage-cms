package com.fortu.player.kiosk

import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException

private const val TAG = "FortuUpdater"

/**
 * Downloads and installs a new APK without anyone touching the screen.
 *
 * **Only works as Device Owner.** Android otherwise shows a confirmation dialog that nobody is
 * standing in front of, which would leave a screen sitting on a permission prompt instead of
 * playing — strictly worse than not updating at all. So this checks first and declines to
 * start rather than half-doing it.
 *
 * Not wired to a trigger yet: the backend has no `apk_url` in its heartbeat response (that is
 * the remaining half of Phase 12c, and it needs a decision about where APKs are hosted). The
 * mechanism is here and testable so that adding the trigger later is a small change rather
 * than a new subsystem.
 */
object SelfUpdater {

    fun isSupported(context: Context) = KioskPolicy.canSilentlyUpdate(context)

    /**
     * Fetch [url] and install it over ourselves. Blocking — call from a background thread.
     * Returns false when silent install isn't available, so a caller can log and move on.
     */
    fun downloadAndInstall(context: Context, client: OkHttpClient, url: String): Boolean {
        if (!isSupported(context)) {
            Log.i(TAG, "not device owner — skipping silent update")
            return false
        }

        val apk = File(context.cacheDir, "update.apk")
        try {
            client.newCall(Request.Builder().url(url).get().build()).execute().use { res ->
                if (!res.isSuccessful) throw IOException("HTTP ${res.code}")
                apk.outputStream().use { out -> res.body!!.byteStream().copyTo(out) }
            }
        } catch (e: Exception) {
            Log.e(TAG, "update download failed", e)
            apk.delete()
            return false
        }

        return try {
            install(context, apk)
            true
        } catch (e: Exception) {
            Log.e(TAG, "update install failed", e)
            false
        } finally {
            // The installer copied it into its own session; ours is just a temp file.
            apk.delete()
        }
    }

    private fun install(context: Context, apk: File) {
        val installer = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(
            PackageInstaller.SessionParams.MODE_FULL_INSTALL
        )
        val sessionId = installer.createSession(params)
        installer.openSession(sessionId).use { session ->
            session.openWrite("fortu", 0, apk.length()).use { out ->
                apk.inputStream().use { it.copyTo(out) }
                session.fsync(out)
            }
            val intent = Intent(context, UpdateResultReceiver::class.java)
            val pending = android.app.PendingIntent.getBroadcast(
                context,
                sessionId,
                intent,
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or
                    android.app.PendingIntent.FLAG_MUTABLE,
            )
            session.commit(pending.intentSender)
        }
        Log.i(TAG, "update committed; the app will restart when it lands")
    }
}
