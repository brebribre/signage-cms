package com.fortu.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Relaunch after a power cut.
 *
 * A signage screen loses power far more often than it crashes — someone switches off the wall
 * socket at closing time. Without this the screen comes back to a launcher instead of the
 * loop, and somebody has to physically visit it.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_LOCKED_BOOT_COMPLETED
        ) {
            context.startActivity(
                Intent(context, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            )
        }
    }
}
