package com.fortu.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.fortu.player.kiosk.KioskPolicy

/**
 * Relaunch after a power cut — a signage screen loses power far more often than it crashes,
 * because someone switches off the wall socket at closing time.
 *
 * **This only works on a screen that is provisioned to allow it.** Since Android 10 an app
 * cannot start an activity from the background, so a plain `startActivity()` from here is
 * silently ignored: no crash, no log, nothing happens. Two configurations make it legal, and
 * both are things a real signage deployment wants anyway:
 *
 *  - **Device Owner** (Phase 12c). `KioskPolicy` registers this app as the persistent
 *    preferred HOME activity, so the system launches it on boot without needing this receiver
 *    at all.
 *  - **The app declared as launcher** — the commented-out HOME intent-filter in
 *    `AndroidManifest.xml`. Same effect, no factory reset required.
 *
 * On an ordinary development install neither applies, and the device boots to its normal
 * launcher. That is the correct behaviour, not a bug — an app that could force itself to the
 * foreground on any phone would be malware.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != Intent.ACTION_LOCKED_BOOT_COMPLETED
        ) {
            return
        }

        if (!KioskPolicy.isDeviceOwner(context)) {
            // Say so rather than attempting a start that the system will discard in silence.
            Log.i(
                "FortuPlayer",
                "boot: not device owner, so the system will not let this app launch itself. " +
                    "Provision as Device Owner or enable the HOME intent-filter — see " +
                    "player/README.md.",
            )
            return
        }

        runCatching {
            context.startActivity(
                Intent(context, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            )
        }.onFailure { Log.e("FortuPlayer", "boot relaunch failed", it) }
    }
}
