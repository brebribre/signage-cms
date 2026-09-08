package com.fortu.player

import android.os.Build
import android.content.pm.ActivityInfo
import android.os.Bundle
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
import com.fortu.player.ui.IdleScreen
import com.fortu.player.ui.PairingScreen
import com.fortu.player.ui.PreparingScreen
import com.fortu.player.ui.StartingScreen
import com.fortu.player.ui.TroubleScreen

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
            var showDebug by remember { mutableStateOf(false) }

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
                    requestedOrientation = when (orientation) {
                        "portrait" -> ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                        "landscape" -> ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                        // Before the first manifest arrives, leave it to the hardware: a
                        // pairing code is legible either way, and forcing a guess would make
                        // the screen visibly flip once the real value lands.
                        else -> ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
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
                    )
                }
                if (showDebug) DebugOverlay(debug)
            }
        }
    }
}
