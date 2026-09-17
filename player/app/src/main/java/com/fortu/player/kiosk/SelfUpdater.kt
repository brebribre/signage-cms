package com.fortu.player.kiosk

import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log
import com.fortu.player.InstallResult
import com.fortu.player.PlayerEngine
import com.fortu.player.api.UpdateInfo
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
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
 * Built for the network it actually runs on — venue wifi that drops for a few seconds at a
 * time. A download that dies partway is resumed from where it stopped (HTTP `Range`), a few
 * times in a row before giving up, and the partial file is kept across the engine's longer
 * backoff so the next attempt picks up the same bytes rather than starting over. Before this
 * existed a single blind GET either finished or didn't, and "didn't" meant a silent ten-minute
 * wait and a full re-download — on a slow link, the same failure again.
 *
 * Triggered from `PlayerEngine.performInstall`, off `HeartbeatResponse.update` — see that
 * class for the retry/backoff policy around a failed attempt and how progress is reported.
 */
object SelfUpdater {

    /** Resume-and-retry within one attempt, before the engine's own cooldown applies. Three
     *  short retries cover the usual wifi blip; anything longer is the engine's problem. */
    private const val DOWNLOAD_ATTEMPTS = 3
    private const val RETRY_PAUSE_MILLIS = 4_000L
    private const val BUFFER_BYTES = 64 * 1024

    fun isSupported(context: Context) = KioskPolicy.canSilentlyUpdate(context)

    /**
     * Fetch [update] and install it over ourselves. Blocking — call from a background thread.
     * [onProgress] is called as bytes land, with the total when it is known (from the offer, or
     * the response), so the screen and the CMS can show a real percentage.
     */
    fun downloadAndInstall(
        context: Context,
        client: OkHttpClient,
        update: UpdateInfo,
        onProgress: (done: Long, total: Long?) -> Unit,
    ): InstallResult {
        if (!isSupported(context)) {
            Log.i(TAG, "not device owner — skipping silent update")
            return InstallResult.Failed(PlayerEngine.NOT_DEVICE_OWNER_REASON)
        }

        val part = partFile(context, update.version)
        // A leftover from a different version is never going to be resumed — the offer that
        // produced it has been superseded. Only ever one partial file on disk at a time.
        context.cacheDir.listFiles { f -> f.name.startsWith("update-") && f != part }
            ?.forEach { it.delete() }

        val downloaded = download(client, update, part, onProgress)
        if (downloaded != null) return InstallResult.Failed(downloaded)

        return try {
            install(context, part)
            part.delete()
            InstallResult.HandedOver
        } catch (e: Exception) {
            Log.e(TAG, "update install failed", e)
            // Not resumable — the installer's copy is what's suspect, so start clean next time.
            part.delete()
            InstallResult.Failed("could not hand the file to the installer: ${e.message ?: e::class.simpleName}")
        }
    }

    /** Null on success; otherwise the reason, for an operator. The partial file is left in
     *  place on failure so the next attempt resumes it. */
    private fun download(
        client: OkHttpClient,
        update: UpdateInfo,
        part: File,
        onProgress: (Long, Long?) -> Unit,
    ): String? {
        val expected = update.bytes
        var lastError = "unknown error"
        for (attempt in 1..DOWNLOAD_ATTEMPTS) {
            try {
                if (expected != null && part.length() > expected) {
                    // Can't be a prefix of the right file. Whatever it is, start over.
                    part.delete()
                }
                if (expected == null || part.length() < expected) {
                    fetch(client, update.url, part, expected, onProgress)
                }
                if (expected != null && part.length() != expected) {
                    throw IOException("got ${part.length()} of $expected bytes")
                }
                onProgress(part.length(), expected ?: part.length())
                return null
            } catch (e: IOException) {
                lastError = e.message ?: e::class.simpleName ?: "I/O error"
                Log.w(TAG, "update download attempt $attempt/$DOWNLOAD_ATTEMPTS failed: $lastError")
                if (attempt < DOWNLOAD_ATTEMPTS) Thread.sleep(RETRY_PAUSE_MILLIS)
            }
        }
        return "download failed after $DOWNLOAD_ATTEMPTS attempts ($lastError)" +
            if (part.length() > 0) " — ${part.length() / 1_048_576} MB kept, will resume" else ""
    }

    /** One HTTP round trip: resume from the end of [part] if there is one, else from zero. */
    private fun fetch(
        client: OkHttpClient,
        url: String,
        part: File,
        expected: Long?,
        onProgress: (Long, Long?) -> Unit,
    ) {
        val have = part.length()
        val builder = Request.Builder().url(url).get()
        if (have > 0) builder.header("Range", "bytes=$have-")
        client.newCall(builder.build()).execute().use { res ->
            val append = when (res.code) {
                206 -> true
                // Range ignored (or nothing to resume): the body is the whole file.
                200 -> false
                416 -> {
                    // The server says our offset is past the end — the partial file is not
                    // a prefix of this object. Start clean on the next attempt.
                    part.delete()
                    throw IOException("HTTP 416 — partial file rejected, restarting")
                }
                else -> throw IOException("HTTP ${res.code}")
            }
            val body = res.body ?: throw IOException("empty response")
            val remaining = body.contentLength().takeIf { it >= 0 }
            val total = when {
                remaining != null -> (if (append) have else 0L) + remaining
                else -> expected
            }
            var done = if (append) have else 0L
            FileOutputStream(part, append).use { out ->
                val buffer = ByteArray(BUFFER_BYTES)
                body.byteStream().use { input ->
                    while (true) {
                        val n = input.read(buffer)
                        if (n == -1) break
                        out.write(buffer, 0, n)
                        done += n
                        onProgress(done, total)
                    }
                }
                out.fd.sync()
            }
        }
    }

    private fun partFile(context: Context, version: String) =
        File(context.cacheDir, "update-$version.apk.part")

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
