package com.fortu.player.kiosk

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log

/** Where PackageInstaller reports whether the silent install actually landed. */
class UpdateResultReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -1)) {
            PackageInstaller.STATUS_SUCCESS ->
                Log.i("FortuUpdater", "update installed")
            PackageInstaller.STATUS_PENDING_USER_ACTION ->
                // Should be unreachable as Device Owner. If it happens, the device is not
                // actually provisioned and the update silently needs a human — worth a loud
                // log rather than a silent stall.
                Log.e("FortuUpdater", "update needs user action — device is not Device Owner")
            else ->
                Log.e(
                    "FortuUpdater",
                    "update failed status=$status " +
                        intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE).orEmpty(),
                )
        }
    }
}
