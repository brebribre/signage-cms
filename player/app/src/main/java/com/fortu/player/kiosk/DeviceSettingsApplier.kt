package com.fortu.player.kiosk

import android.content.Context
import android.media.AudioManager
import android.os.PowerManager
import android.provider.Settings
import android.util.Log
import com.fortu.player.api.ManifestSettings
import kotlinx.serialization.json.JsonPrimitive

private const val TAG = "FortuSettings"

/**
 * Applies the [ManifestSettings] fields that are genuine system side effects — volume,
 * brightness, and power. `app_password` is read-only state compared by the exit-PIN dialog in
 * `MainActivity`, and `touchscreen_disabled` isn't applied by this build at all (see `Models.kt`'s
 * `ManifestSettings` doc).
 *
 * Power is the odd one out: *what* it should be is decided over time by `PlayerEngine` from the
 * schedule and override (`power/PowerPlan.kt`), not read off the manifest once — so it isn't in
 * [apply]. [applyPower] is only the mechanism the engine calls when that decision changes.
 *
 * Same trust tier as [KioskPolicy]: every call here degrades to a logged no-op rather than a
 * crash, because this same APK also runs on a developer's phone and an emulator where none of
 * it should — or safely can — take effect.
 */
object DeviceSettingsApplier {

    /** What this process last actually applied for each field — in memory only, never
     *  persisted, so a fresh process (a reboot, an app restart) always applies its restored
     *  settings unconditionally on the first call, exactly as before. What this skips is
     *  *redundant* re-application within an already-running process: the manifest bundles
     *  settings in with content (see `device_sync.compute_version`'s docstring), so an
     *  unrelated change — a new playlist, a different orientation — produces a new manifest
     *  and would otherwise re-apply every setting every time, even ones that did not change.
     *  That is more than wasted work: it means a volume nudge made by hand at the screen gets
     *  silently overwritten back to the CMS's last-known value the next time anything else
     *  changes, not only when someone actually touches volume. */
    private var lastAppliedVolume: Int? = null
    private var lastAppliedBrightness: Int? = null

    fun apply(context: Context, settings: ManifestSettings) {
        settings.volume?.let {
            if (it != lastAppliedVolume) { applyVolume(context, it); lastAppliedVolume = it }
        }
        settings.brightness?.let {
            if (it != lastAppliedBrightness) { applyBrightness(context, it); lastAppliedBrightness = it }
        }
    }

    /**
     * What the screen's settings actually are right now, read straight from the system rather
     * than from whatever was last applied — the CMS shows this next to the value it wants, and
     * the two are allowed to disagree (a change still in flight, someone turning the volume up
     * by hand, a power-off that this screen isn't provisioned to perform). Brightness is
     * included even off Device Owner: reading it needs no special access, only *writing* it
     * does.
     */
    fun currentSettings(context: Context): Map<String, JsonPrimitive> {
        val out = mutableMapOf<String, JsonPrimitive>()
        runCatching {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            if (max > 0) {
                val current = am.getStreamVolume(AudioManager.STREAM_MUSIC)
                out["volume"] = JsonPrimitive((current * 100 + max / 2) / max) // rounded, not floored
            }
        }.onFailure { Log.w(TAG, "reading volume failed", it) }
        runCatching {
            val level = Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS)
            out["brightness"] = JsonPrimitive((level * 100 + 127) / 255)
        }.onFailure { Log.w(TAG, "reading brightness failed", it) }
        runCatching {
            val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            out["power_state"] = JsonPrimitive(if (pm.isInteractive) "on" else "off")
        }.onFailure { Log.w(TAG, "reading power state failed", it) }
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
            // Adaptive brightness is the factory default on most hardware, and it silently
            // overrides any value written below within moments — the write above was landing
            // and then immediately getting clobbered by the light sensor. Forcing manual mode
            // first is what actually makes the value stick.
            Settings.System.putInt(
                context.contentResolver, Settings.System.SCREEN_BRIGHTNESS_MODE,
                Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL,
            )
            Settings.System.putInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, level)
        }.onFailure { Log.w(TAG, "brightness apply failed", it) }
    }

    /**
     * Software sleep/wake, not a true hardware power cycle — there is no generic AOSP API to
     * cut power to an HDMI-connected TV. Whether the physical TV actually goes to standby
     * when this box sleeps depends on the TV honoring HDMI-CEC, which is set-dependent and
     * outside this app's control. Called by `PlayerEngine` only when its power decision
     * changes; the actual result is reported back as `power_state` by [currentSettings].
     */
    fun applyPower(context: Context, on: Boolean) {
        if (on) {
            wakeScreen(context)
            return
        }
        if (!KioskPolicy.isDeviceOwner(context)) {
            Log.i(TAG, "power off requested but not device owner — skipped (see player/README.md)")
            return
        }
        // lockNow() needs only the force-lock policy this app already declares (see
        // res/xml/device_admin.xml) — no extra provisioning beyond Device Owner itself.
        runCatching { KioskPolicy.dpm(context).lockNow() }
            .onFailure { Log.w(TAG, "power off failed", it) }
    }

    @Suppress("DEPRECATION") // SCREEN_BRIGHT_WAKE_LOCK has no non-deprecated equivalent that
    // works from a plain Context rather than a foreground Activity.
    private fun wakeScreen(context: Context) {
        runCatching {
            val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            val wakeLock = pm.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK or
                    PowerManager.ACQUIRE_CAUSES_WAKEUP or
                    PowerManager.ON_AFTER_RELEASE,
                "$TAG:wake",
            )
            // Only needs to hold long enough to trigger the wake — the keyguard is already
            // disabled (KioskPolicy.apply), so nothing re-locks the screen once it's on.
            wakeLock.acquire(3_000)
        }.onFailure { Log.w(TAG, "power on (wake) failed", it) }
    }
}
