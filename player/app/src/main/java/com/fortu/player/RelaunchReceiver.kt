package com.fortu.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.fortu.player.kiosk.KioskPolicy

/**
 * Bring the player back after a self-update, which kills the app as part of installing over it.
 *
 * The installer's own result broadcast (`kiosk/UpdateResultReceiver`) is addressed to a
 * PendingIntent owned by the build being replaced, and on real boxes it often never arrives
 * after the replacement — the screen sat on the launcher until someone pressed Home.
 * `ACTION_MY_PACKAGE_REPLACED` is the signal Android delivers to the *new* build for exactly
 * this; if both arrive, the second start just fronts the activity that is already up.
 *
 * **Deliberately not a boot receiver.** The player does not open itself after a reboot or a
 * power cut: the screen comes back to its normal launcher and whoever is there taps the app.
 * A screen is sometimes wanted for something else, and an app that put itself in front on every
 * boot would make that a fight. An update is different — the app was running when it happened,
 * so coming back is what was already on screen. See "After a reboot" in player/README.md.
 *
 * Only a Device Owner build can start an activity from the background (Android 10+ discards a
 * plain `startActivity()` from here in silence), so on any other install this logs and stops.
 */
class RelaunchReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        Log.i("FortuPlayer", "updated — relaunching")

        if (!KioskPolicy.isDeviceOwner(context)) {
            Log.i(
                "FortuPlayer",
                "not device owner, so the system will not let this app launch itself after the update",
            )
            return
        }

        runCatching {
            context.startActivity(
                Intent(context, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            )
        }.onFailure { Log.e("FortuPlayer", "relaunch after update failed", it) }
    }
}
