package com.fortu.player.data

import android.content.Context
import android.util.Log
import com.fortu.player.api.ManifestItem
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException

/**
 * Files on local disk, keyed by **checksum**.
 *
 * That key is the whole design. The manifest's presigned URLs expire every 6 hours and are
 * re-issued on every fetch, so keying on URL would re-download the entire playlist several
 * times a day. The checksum is the content's identity and never changes, so a re-issued URL
 * for unchanged content is recognised as already-downloaded.
 */
class MediaCache(context: Context) {
    private val dir = File(context.filesDir, "media").apply { mkdirs() }

    private fun safeName(checksum: String) = checksum.replace(Regex("[^A-Za-z0-9]"), "_")

    fun fileFor(checksum: String): File = File(dir, safeName(checksum))

    fun isCached(item: ManifestItem): Boolean {
        val f = fileFor(item.checksum)
        // Size check as well as existence: a download interrupted by a power cut leaves a
        // short file behind, and playing that is worse than re-fetching it.
        return f.exists() && f.length() == item.bytes
    }

    @Throws(IOException::class)
    fun download(client: OkHttpClient, item: ManifestItem) {
        val target = fileFor(item.checksum)
        // Write to a temp file and rename only on success, so an interrupted download can
        // never be mistaken for a complete one.
        val tmp = File(target.absolutePath + ".part")
        val req = Request.Builder().url(item.url).get().build()
        client.newCall(req).execute().use { res ->
            if (!res.isSuccessful) throw IOException("download failed: HTTP ${res.code}")
            tmp.outputStream().use { out -> res.body!!.byteStream().copyTo(out) }
        }
        if (!tmp.renameTo(target)) {
            tmp.delete()
            throw IOException("could not finalise ${target.name}")
        }
    }

    /**
     * Delete anything not in the current manifest.
     *
     * Called only **after** every new item has downloaded successfully — evicting first would
     * risk leaving a screen with a half-empty cache if the network died mid-swap.
     */
    fun evictExcept(keep: Collection<String>) {
        val keepNames = keep.map(::safeName).toSet()
        dir.listFiles()?.forEach { f ->
            if (f.name !in keepNames) {
                if (f.delete()) Log.i("MediaCache", "evicted ${f.name}")
            }
        }
    }

    fun cachedBytes(): Long = dir.listFiles()?.sumOf { it.length() } ?: 0L
}
