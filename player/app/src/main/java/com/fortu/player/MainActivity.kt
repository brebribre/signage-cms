package com.fortu.player

import android.os.Build
import android.content.pm.ActivityInfo
import android.os.Bundle
import android.util.Log
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.fortu.player.kiosk.KioskPolicy
import com.fortu.player.playback.PlaybackSurface
import com.fortu.player.ui.ClaimedScreen
import com.fortu.player.ui.DebugOverlay
import com.fortu.player.ui.ExitPinDialog
import com.fortu.player.ui.IdleScreen
import com.fortu.player.ui.PairingScreen
import com.fortu.player.ui.PreparingScreen
import com.fortu.player.ui.StartingScreen
import com.fortu.player.ui.TroubleScreen
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val vm: PlayerViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // A signage screen must never sleep, and must never show system chrome.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, window.decorView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }

        // Idempotent, and a no-op unless this app is Device Owner — so the same APK is safe
        // on a developer's phone, an emulator, and a provisioned panel.
        KioskPolicy.apply(this)

        vm.setKioskState(KioskPolicy.describe(this))

        val metrics = resources.displayMetrics
        vm.setScreenSize(metrics.widthPixels, metrics.heightPixels)
        vm.start()

        setContent {
            val state by vm.state.collectAsState()
            val debug by vm.debug.collectAsState()
            val settings by vm.settings.collectAsState()
            var showDebug by remember { mutableStateOf(false) }
            var showExitPin by remember { mutableStateOf(false) }
            var exitPinError by remember { mutableStateOf(false) }
            var appliedOrientation by remember { mutableStateOf<String?>(null) }

            Box(
                Modifier
                    .fillMaxSize()
                    // Long-press is the only input this app has. There is no keyboard on a
                    // signage screen, and a visible button would eventually get tapped by a
                    // member of the public.
                    .pointerInput(Unit) {
                        detectTapGestures(onLongPress = { showDebug = !showDebug })
                    }
            ) {
                // Applied from the CMS rather than fixed in the manifest, so one APK serves
                // portrait totems and landscape panels. Re-applied whenever the value
                // changes, since a screen can be re-oriented without being re-paired.
                LaunchedEffect(state) {
                    val orientation = when (val s = state) {
                        is PlayerState.Playing -> s.orientation
                        is PlayerState.Idle -> s.orientation
                        else -> null
                    }
                    if (orientation != appliedOrientation) {
                        // Lock Task Mode (Device Owner builds only — see KioskPolicy.apply)
                        // freezes whatever orientation was active when it started and ignores
                        // requestedOrientation changes after that. Cycling out of and back
                        // into lock task around the change is the documented workaround; a
                        // no-op pair of calls on a non-owner build, which was never locked.
                        val locked = KioskPolicy.isDeviceOwner(this@MainActivity)
                        if (locked) runCatching { stopLockTask() }
                        requestedOrientation = when (orientation) {
                            "portrait" -> ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                            "landscape" -> ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                            // Before the first manifest arrives, leave it to the hardware: a
                            // pairing code is legible either way, and forcing a guess would
                            // make the screen visibly flip once the real value lands.
                            else -> ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
                        }
                        if (locked) runCatching { startLockTask() }
                        appliedOrientation = orientation
                    }
                }

                // Nobody is meant to leave this open — it's a diagnostics view, not a mode.
                // Restarted whenever showExitPin changes too, so entering a PIN doesn't get
                // cut off mid-entry by the same countdown that dismisses an idle overlay — and
                // whenever the update status changes, so tapping "Check for update" gets a
                // fresh 10 seconds to actually show the result instead of vanishing mid-check.
                LaunchedEffect(showDebug, showExitPin, debug.updateStatus) {
                    if (showDebug && !showExitPin) {
                        delay(10_000)
                        showDebug = false
                    }
                }

                when (val s = state) {
                    is PlayerState.Starting -> StartingScreen()
                    is PlayerState.Pairing -> PairingScreen(s.code, s.apiHost, s.error, s.checks)
                    is PlayerState.Claimed -> ClaimedScreen(s.deviceName)
                    is PlayerState.Preparing ->
                        PreparingScreen(s.deviceName, s.done, s.total, s.currentFile)
                    is PlayerState.Idle -> IdleScreen(s.deviceName)
                    is PlayerState.Trouble ->
                        TroubleScreen(s.deviceName, s.message, s.apiHost, s.attempts)
                    is PlayerState.Playing -> PlaybackSurface(
                        items = s.items,
                        fileFor = vm::localFileFor,
                        onPlayed = vm::reportPlay,
                        onPlaybackError = vm::reportError,
                    )
                }
                if (showDebug) {
                    DebugOverlay(
                        debug,
                        onExitRequested = {
                            val pin = settings.appPassword
                            if (pin.isNullOrBlank()) {
                                exitKiosk()
                                showDebug = false
                            } else {
                                exitPinError = false
                                showExitPin = true
                            }
                        },
                        onCheckUpdateRequested = vm::checkForUpdateNow,
                    )
                }
                if (showExitPin) {
                    ExitPinDialog(
                        error = exitPinError,
                        onDismiss = { showExitPin = false },
                        onSubmit = { entered ->
                            if (entered == settings.appPassword) {
                                showExitPin = false
                                showDebug = false
                                exitKiosk()
                            } else {
                                exitPinError = true
                            }
                        },
                    )
                }
            }
        }
    }

    /** Lifts lock task mode so the device's normal navigation becomes reachable again — the
     *  one exit this app has. A no-op, logged rather than crashing, when the device was never
     *  in lock task to begin with (not Device Owner, or already out of it). */
    private fun exitKiosk() {
        runCatching { stopLockTask() }
            .onFailure { Log.w("FortuPlayer", "stopLockTask failed", it) }
    }
}
