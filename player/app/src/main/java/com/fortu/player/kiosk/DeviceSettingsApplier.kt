package com.fortu.player.kiosk

import android.content.Context
import android.media.AudioManager
import android.provider.Settings
import android.util.Log
import com.fortu.player.api.ManifestSettings

private const val TAG = "FortuSettings"

/**
 * Applies the two [ManifestSettings] fields that are genuine system side effects — volume and
 * brightness. `app_password` is read-only state compared by the exit-PIN dialog in
 * `MainActivity`, and `touchscreen_disabled`/`power_schedule` aren't applied by this build at
 * all (see `Models.kt`'s `ManifestSettings` doc).
 *
 * Same trust tier as [KioskPolicy]: every call here degrades to a logged no-op rather than a
 * crash, because this same APK also runs on a developer's phone and an emulator where none of
 * it should — or safely can — take effect.
 */
object DeviceSettingsApplier {

    fun apply(context: Context, settings: ManifestSettings) {
        settings.volume?.let { applyVolume(context, it) }
        settings.brightness?.let { applyBrightness(context, it) }
    }

    /**
     * What volume and brightness actually are right now, read straight from the system
     * rather than from whatever was last applied — the CMS shows this next to the value it
     * wants, and the two are allowed to disagree (a change still in flight, someone turning
     * the volume up by hand at the screen). Brightness is included even off Device Owner:
     * reading it needs no special access, only *writing* it does.
     */
    fun currentSettings(context: Context): Map<String, Int> {
        val out = mutableMapOf<String, Int>()
        runCatching {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            if (max > 0) {
                val current = am.getStreamVolume(AudioManager.STREAM_MUSIC)
                out["volume"] = (current * 100 + max / 2) / max // rounded, not floored
            }
        }.onFailure { Log.w(TAG, "reading volume failed", it) }
        runCatching {
            val level = Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS)
            out["brightness"] = (level * 100 + 127) / 255
        }.onFailure { Log.w(TAG, "reading brightness failed", it) }
        return out
    }

    private fun applyVolume(context: Context, percent: Int) {
        val clamped = percent.coerceIn(0, 100)
        runCatching {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val level = (clamped * max + 50) / 100 // rounded, not floored
            am.setStreamVolume(AudioManager.STREAM_MUSIC, level, 0)
        }.onFailure { Log.w(TAG, "volume apply failed", it) }
    }

    /**
     * `Settings.System.SCREEN_BRIGHTNESS` sits behind the `WRITE_SETTINGS` app-op, which a
     * normal install can only get by sending the user through a system settings screen — not
     * something a signage box with no keyboard and nobody in front of it can do. Device Owner
     * apps write it directly; anything else logs and skips, same as every other line in
     * [KioskPolicy.apply].
     */
    private fun applyBrightness(context: Context, percent: Int) {
        if (!KioskPolicy.isDeviceOwner(context)) {
            Log.i(TAG, "brightness set requested but not device owner — skipped (see player/README.md)")
            return
        }
        val clamped = percent.coerceIn(0, 100)
        val level = (clamped * 255 + 50) / 100
        runCatching {
            Settings.System.putInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, level)
        }.onFailure { Log.w(TAG, "brightness apply failed", it) }
    }
}
