package com.fortu.player.kiosk

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * The component `dpm set-device-owner` targets.
 *
 * Its existence is what makes Device Owner possible at all — without a registered admin
 * receiver the provisioning command has nothing to point at. It needs no logic of its own;
 * the policy is applied by [KioskPolicy] once ownership is granted.
 */
class DeviceAdminReceiver : DeviceAdminReceiver() {
    override fun onEnabled(context: Context, intent: Intent) {
        Log.i("FortuKiosk", "device admin enabled")
    }

    override fun onDisabled(context: Context, intent: Intent) {
        Log.w("FortuKiosk", "device admin disabled — kiosk protections are gone")
    }
}
