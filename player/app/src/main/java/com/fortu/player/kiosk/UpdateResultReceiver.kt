package com.fortu.player.kiosk

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log
import com.fortu.player.MainActivity

private const val TAG = "FortuUpdater"

/**
 * Where PackageInstaller reports whether the silent install actually landed.
 *
 * A self-update kills this process as part of installing over it — nothing sends the HOME
 * intent that `KioskPolicy`'s persistent-preferred-launcher setting responds to, so without
 * this the screen would sit on the bare Android launcher, alive in the background but showing
 * nothing, until the next reboot (`BootReceiver`) or a human pressed Home. Confirmed live on
 * an emulator: the update installed correctly and the process kept running, but the activity
 * never came back on its own.
 */
class UpdateResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -1)) {
            PackageInstaller.STATUS_SUCCESS -> {
                Log.i(TAG, "update installed")
                relaunch(context)
            }
            PackageInstaller.STATUS_PENDING_USER_ACTION ->
                // Should be unreachable as Device Owner. If it happens, the device is not
                // actually provisioned and the update silently needs a human — worth a loud
                // log rather than a silent stall.
                Log.e(TAG, "update needs user action — device is not Device Owner")
            else ->
                Log.e(
                    TAG,
                    "update failed status=$status " +
                        intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE).orEmpty(),
                )
        }
    }

    /** Same pattern as `BootReceiver` — a plain `startActivity()` from a background receiver
     *  needs the Device Owner exemption to actually take effect, which is guaranteed here
     *  since only a Device Owner screen ever reaches a silent install in the first place. */
    private fun relaunch(context: Context) {
        if (!KioskPolicy.isDeviceOwner(context)) return
        runCatching {
            context.startActivity(
                Intent(context, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            )
        }.onFailure { Log.e(TAG, "post-update relaunch failed", it) }
    }
}
