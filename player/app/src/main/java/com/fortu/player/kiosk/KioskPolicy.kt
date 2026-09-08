package com.fortu.player.kiosk

import android.app.Activity
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log

private const val TAG = "FortuKiosk"

/**
 * Everything that keeps a screen showing content and nothing else.
 *
 * All of it degrades: on a device where this app is **not** Device Owner, every call here is
 * a no-op or falls back to screen pinning. That matters because the same APK has to run on a
 * developer's phone, an emulator, and a factory-reset panel — and on the first two it must not
 * try to take over the device.
 */
object KioskPolicy {

    fun admin(context: Context) = ComponentName(context, DeviceAdminReceiver::class.java)

    fun dpm(context: Context): DevicePolicyManager =
        context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager

    fun isDeviceOwner(context: Context): Boolean =
        dpm(context).isDeviceOwnerApp(context.packageName)

    /**
     * Apply the full policy. Safe to call on every launch — each setting is idempotent, and
     * re-applying costs nothing.
     */
    fun apply(activity: Activity) {
        val context = activity.applicationContext
        val dpm = dpm(context)
        val admin = admin(context)

        if (!isDeviceOwner(context)) {
            // Deliberately does nothing. Calling startLockTask() without Device Owner does
            // not "fall back to screen pinning" — the task is not allowlisted, so the system
            // refuses it and logs an "Attempted Lock Task Mode violation" on every launch.
            // Screen pinning on an unprovisioned device is a thing the *user* turns on from
            // system settings; the app cannot grant it to itself, and pretending otherwise
            // only produced log noise that looked like a fault.
            Log.i(TAG, "not device owner — kiosk policy skipped (see player/README.md)")
            return
        }

        // Only this app may run in lock task mode, so nothing else can take the foreground.
        runCatching {
            dpm.setLockTaskPackages(admin, arrayOf(context.packageName))
            activity.startLockTask()
        }.onFailure { Log.w(TAG, "lock task setup failed", it) }

        // Stay on while plugged in — a signage screen is always plugged in, and this is
        // belt-and-braces alongside FLAG_KEEP_SCREEN_ON in the activity.
        runCatching {
            dpm.setGlobalSetting(
                admin,
                Settings.Global.STAY_ON_WHILE_PLUGGED_IN,
                "7", // AC | USB | wireless
            )
        }.onFailure { Log.w(TAG, "stay-on failed", it) }

        // A system update prompt covering the screen is exactly the interruption this whole
        // phase exists to prevent. Defer them to a window nobody is looking.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            runCatching {
                dpm.setSystemUpdatePolicy(
                    admin,
                    android.app.admin.SystemUpdatePolicy.createWindowedInstallPolicy(180, 300),
                )
            }.onFailure { Log.w(TAG, "update policy failed", it) }
        }

        // No lock screen to get stuck behind after a reboot.
        runCatching { dpm.setKeyguardDisabled(admin, true) }
            .onFailure { Log.w(TAG, "keyguard disable failed", it) }

        // Make this app the persistent preferred launcher, so HOME returns here and a reboot
        // lands in the player rather than a desktop. Done through the policy rather than the
        // manifest's HOME intent-filter so a non-owner install never hijacks a real phone.
        runCatching {
            val filter = android.content.IntentFilter(android.content.Intent.ACTION_MAIN).apply {
                addCategory(android.content.Intent.CATEGORY_HOME)
                addCategory(android.content.Intent.CATEGORY_DEFAULT)
            }
            dpm.addPersistentPreferredActivity(
                admin,
                filter,
                ComponentName(context, com.fortu.player.MainActivity::class.java),
            )
        }.onFailure { Log.w(TAG, "preferred launcher failed", it) }

        Log.i(TAG, "device owner policy applied")
    }

    /** True when this build can install an APK without any user interaction. */
    fun canSilentlyUpdate(context: Context): Boolean = isDeviceOwner(context)

    /** Human-readable state for the debug overlay. */
    fun describe(context: Context): String = when {
        isDeviceOwner(context) -> "device owner (full kiosk)"
        else -> "not owner (screen pinning only)"
    }
}
