package com.fortu.player

import android.os.Build
import android.os.Handler
import android.os.Looper
import android.content.pm.ActivityInfo
import android.os.Bundle
import android.util.Log
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
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
import kotlin.math.hypot

class MainActivity : ComponentActivity() {
    private val vm: PlayerViewModel by viewModels()

    /** Activity-level rather than inside setContent, so the Menu key can open it too. */
    private var showDebug by mutableStateOf(false)

    private var touchDownX = 0f
    private var touchDownY = 0f
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pendingLongPress: Runnable? = null

    /**
     * Two jobs, both of which have to happen before anything else sees the touch.
     *
     * The CMS's touchscreen lock: every touch on this window is dropped — playback, the website
     * a scene is showing, the corner gesture below, all of it. Only touches are affected. System
     * edge gestures never reach an app window anyway; in lock task mode they're already blocked
     * (see KioskPolicy), and the lock can't reach them either way.
     *
     * The hidden gesture that opens the debug overlay: hold the top-left corner. Recognised here
     * rather than in Compose, and on a timer from touch-down rather than on touch-up, because a
     * website element is a WebView that handles its own touches (people are meant to be able to
     * use it) — it answers a long press with its own text-selection menu, and the app window
     * never sees the press end. Confined to the corner so using a page never trips it. The touch
     * itself is always passed on, so the page loses nothing.
     */
    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        if (vm.settings.value.touchscreenDisabled == true) return true
        when (ev.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                touchDownX = ev.x
                touchDownY = ev.y
                if (inHiddenCorner(ev.x, ev.y)) {
                    val fire = Runnable {
                        pendingLongPress = null
                        showDebug = !showDebug
                    }
                    pendingLongPress = fire
                    mainHandler.postDelayed(fire, LONG_PRESS_MILLIS)
                }
            }
            MotionEvent.ACTION_MOVE -> {
                val slopPx = LONG_PRESS_SLOP_DP * resources.displayMetrics.density
                if (hypot(ev.x - touchDownX, ev.y - touchDownY) > slopPx) cancelLongPress()
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> cancelLongPress()
        }
        return super.dispatchTouchEvent(ev)
    }

    /** Top-left corner, as a fraction of the screen — big enough to hit without looking, small
     *  enough to stay out of the way of whatever is playing. */
    private fun inHiddenCorner(x: Float, y: Float): Boolean {
        val metrics = resources.displayMetrics
        return x <= metrics.widthPixels * HIDDEN_CORNER_FRACTION &&
            y <= metrics.heightPixels * HIDDEN_CORNER_FRACTION
    }

    private fun cancelLongPress() {
        pendingLongPress?.let(mainHandler::removeCallbacks)
        pendingLongPress = null
    }

    /** Menu on a USB keyboard or remote opens the debug overlay. That is the local way out
     *  when touch is locked: Tab to "Exit kiosk", Enter, type the PIN. */
    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.keyCode == KeyEvent.KEYCODE_MENU) {
            if (event.action == KeyEvent.ACTION_UP) showDebug = !showDebug
            return true
        }
        return super.dispatchKeyEvent(event)
    }

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
            var showExitPin by remember { mutableStateOf(false) }
            var exitPinError by remember { mutableStateOf(false) }
            val orientation by vm.orientation.collectAsState()

            // The corner hold that opens the debug overlay is recognised in dispatchTouchEvent
            // above, not here — see its comment.
            Box(Modifier.fillMaxSize()) {
                // Applied from the CMS rather than fixed in the manifest, so one APK serves
                // portrait totems and landscape panels. Re-applied whenever the value
                // changes, since a screen can be re-oriented without being re-paired.
                LaunchedEffect(orientation) {
                    // Before the first manifest arrives, leave it to the hardware: a pairing
                    // code is legible either way, and forcing a guess would make the screen
                    // visibly flip once the real value lands.
                    val target = when (orientation) {
                        "portrait" -> ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                        "landscape" -> ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                        else -> null
                    } ?: return@LaunchedEffect
                    // Lock Task Mode (Device Owner builds only — see KioskPolicy.apply)
                    // freezes whatever orientation was active when it started and ignores
                    // requestedOrientation changes after that. Cycling out of and back
                    // into lock task around the change is the documented workaround; a
                    // no-op pair of calls on a non-owner build, which was never locked.
                    val locked = KioskPolicy.isDeviceOwner(this@MainActivity)
                    if (locked) runCatching { stopLockTask() }
                    requestedOrientation = target
                    if (locked) runCatching { startLockTask() }
                }

                // A lock landing while someone is at the screen closes what they had open by
                // touch. The PIN dialog is its own window, so dispatchTouchEvent can't reach it.
                LaunchedEffect(settings.touchscreenDisabled) {
                    if (settings.touchscreenDisabled == true) {
                        showExitPin = false
                        showDebug = false
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
                    is PlayerState.Pairing -> PairingScreen(s.code, s.error)
                    is PlayerState.Claimed -> ClaimedScreen(s.deviceName)
                    is PlayerState.Preparing ->
                        PreparingScreen(s.deviceName, s.done, s.total, s.currentFile)
                    is PlayerState.Idle -> IdleScreen(s.deviceName)
                    is PlayerState.Trouble ->
                        TroubleScreen(s.deviceName, s.message, s.apiHost, s.attempts)
                    is PlayerState.Playing -> PlaybackSurface(
                        slots = s.slots,
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
    private companion object {
        /** Deliberately longer than the system's own long-press, so a page's own long-press
         *  (selecting text) in the corner is not immediately also this. */
        const val LONG_PRESS_MILLIS = 900L
        const val LONG_PRESS_SLOP_DP = 24f
        const val HIDDEN_CORNER_FRACTION = 0.2f
    }

    private fun exitKiosk() {
        runCatching { stopLockTask() }
            .onFailure { Log.w("FortuPlayer", "stopLockTask failed", it) }
    }
}
