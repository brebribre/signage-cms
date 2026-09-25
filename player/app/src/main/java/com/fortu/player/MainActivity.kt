package com.fortu.player

import android.os.Build
import android.os.Handler
import android.os.Looper
import android.content.Intent
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
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.fortu.player.kiosk.DeviceSettingsApplier
import com.fortu.player.kiosk.KioskPolicy
import com.fortu.player.playback.PlaybackSurface
import com.fortu.player.ui.ClaimedScreen
import com.fortu.player.ui.DebugOverlay
import com.fortu.player.ui.LeavePinDialog
import com.fortu.player.ui.IdleScreen
import com.fortu.player.ui.SleepScreen
import com.fortu.player.ui.PairingScreen
import com.fortu.player.ui.PreparingScreen
import com.fortu.player.ui.StartingScreen
import com.fortu.player.ui.TroubleScreen
import com.fortu.player.ui.UpdateBanner
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
     *  when touch is locked: Tab to "Leave player", Enter, type the PIN. */
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
        // When a scheduled "on" wakes the display (DeviceSettingsApplier.wakeScreen), the
        // player must be what appears — over a swipe lock screen on a box that has one, which
        // no policy is needed for. Device Owner boxes have no keyguard at all.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
            )
        }
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
            val asleep by DeviceSettingsApplier.asleep.collectAsState()

            // Asleep: the window stops holding the panel awake, so the box's own sleep timer
            // may switch the display off, and its brightness goes to the floor so a panel that
            // stays lit is as dark as it can be. Both are per-window and need no policy. Both
            // come back the moment the screen is on again.
            LaunchedEffect(asleep) {
                if (asleep) window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                else window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                window.attributes = window.attributes.apply {
                    screenBrightness = if (asleep) 0f
                    else WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
                }
            }

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
                    // Degrees are the rotation of the content, clockwise, from the panel's own
                    // landscape: 90 and 270 are the two ways a totem can be stood on its side,
                    // which "portrait" alone could never tell apart.
                    val target = when (orientation) {
                        "0", "landscape" -> ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                        "90", "portrait" -> ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                        "180" -> ActivityInfo.SCREEN_ORIENTATION_REVERSE_LANDSCAPE
                        "270" -> ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT
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

                // Asleep means nothing playing at all, not content hidden behind black: a
                // sleeping screen should not be decoding video all night. Leaving the
                // composition releases every player and WebView; waking rebuilds them.
                if (asleep) SleepScreen() else when (val s = state) {
                    is PlayerState.Starting -> StartingScreen()
                    is PlayerState.Pairing -> PairingScreen(s.code, s.error)
                    is PlayerState.Claimed -> ClaimedScreen(s.deviceName)
                    is PlayerState.Preparing ->
                        PreparingScreen(s.deviceName, s.doneBytes, s.totalBytes, s.currentFile, s.bytesPerSecond)
                    is PlayerState.Idle -> IdleScreen(s.deviceName)
                    is PlayerState.Trouble ->
                        TroubleScreen(s.deviceName, s.message, s.apiHost, s.attempts)
                    // Keyed on the generation so the engine's stall watchdog can rebuild the
                    // whole surface — timers, players and all — by bumping one number.
                    is PlayerState.Playing -> key(s.generation) {
                        PlaybackSurface(
                            slots = s.slots,
                            liveSlotId = s.liveSlotId,
                            fileFor = vm::localFileFor,
                            onPlayed = vm::reportPlay,
                            onPlaybackError = vm::reportError,
                            onVideoStats = vm::reportVideoStats,
                        )
                    }
                }
                // A small card at the bottom while a build downloads or installs, and for a
                // couple of minutes after a failure — the on-screen half of what the CMS
                // shows for the same install, so nobody at the screen is left guessing either.
                val update = debug.update
                var bannerVisible by remember(update) { mutableStateOf(update != null) }
                LaunchedEffect(update) {
                    if (update?.phase == UpdatePhase.FAILED) {
                        delay(UPDATE_FAILURE_BANNER_MILLIS)
                        bannerVisible = false
                    }
                }
                if (update != null && bannerVisible) UpdateBanner(update)

                if (showDebug) {
                    DebugOverlay(
                        debug,
                        onLeaveRequested = {
                            val pin = settings.appPassword
                            if (pin.isNullOrBlank()) {
                                showDebug = false
                                leavePlayer()
                            } else {
                                exitPinError = false
                                showExitPin = true
                            }
                        },
                        onCheckUpdateRequested = vm::checkForUpdateNow,
                    )
                }
                if (showExitPin) {
                    LeavePinDialog(
                        error = exitPinError,
                        onDismiss = { showExitPin = false },
                        onSubmit = { entered ->
                            if (entered == settings.appPassword) {
                                showExitPin = false
                                showDebug = false
                                leavePlayer()
                            } else {
                                exitPinError = true
                            }
                        },
                    )
                }
            }
        }
    }

    /** Every return to the player locks it again, so "Leave player" lasts only until someone
     *  opens the player. Without this, coming back after an exit left it unlocked and the next
     *  exit needed no PIN. See KioskPolicy.relock. */
    override fun onResume() {
        super.onResume()
        KioskPolicy.relock(this)
    }

    private companion object {
        /** Deliberately longer than the system's own long-press, so a page's own long-press
         *  (selecting text) in the corner is not immediately also this. */
        const val LONG_PRESS_MILLIS = 900L
        const val LONG_PRESS_SLOP_DP = 24f
        const val HIDDEN_CORNER_FRACTION = 0.2f
        /** How long a failed update stays announced on screen. Long enough to be read by
         *  whoever is walking over; the debug overlay keeps the reason after that. */
        const val UPDATE_FAILURE_BANNER_MILLIS = 120_000L
    }

    /** The one way out this app has: lift lock task mode, then open the Android home screen.
     *
     *  Going home is the point. Lifting the lock alone changed nothing anyone could see — the
     *  player stayed on screen, and only a swipe from the edge showed that Home and Back worked
     *  again — so the button looked broken. The lock must come off first, because while it is
     *  on Android refuses to start another app's screen. Lifting it is a no-op, logged rather
     *  than crashing, when the device was never locked (not Device Owner); going home still
     *  happens, so the button does the same thing everywhere. The lock comes back the next
     *  time the player is on screen (onResume). */
    private fun leavePlayer() {
        runCatching { stopLockTask() }
            .onFailure { Log.w("FortuPlayer", "stopLockTask failed", it) }
        val home = Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_HOME)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        runCatching { startActivity(home) }
            .onFailure {
                // No launcher to go to (rare on a stripped box): step aside instead, which
                // shows whatever is underneath.
                Log.w("FortuPlayer", "opening the home screen failed", it)
                moveTaskToBack(true)
            }
    }
}
