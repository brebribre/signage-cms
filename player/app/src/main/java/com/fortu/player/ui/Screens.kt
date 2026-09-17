package com.fortu.player.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fortu.player.DebugInfo
import com.fortu.player.UpdatePhase
import com.fortu.player.UpdateProgress
import com.fortu.player.R

// Paskall's palette — the same tokens as the CMS (frontend/src/style.css) and the web player.
private val Ink = Color(0xFF101111)
private val InkInverse = Color(0xFFF9F9F9)
private val InkMuted = Color(0xFF7D7D7D)
private val InkSubtle = Color(0xFF4A4A4A)
private val BrandStrong = Color(0xFF002F96)
private val Brand = Color(0xFF003399)
private val BrandBright = Color(0xFF0076DD)
/** Secondary text on the brand gradient. */
private val OnBrandMuted = Color.White.copy(alpha = 0.78f)

/** The CMS's hero-card gradient, corner to corner, as a screen background. */
private val BrandGradient = Brush.linearGradient(
    0f to BrandStrong,
    0.45f to Brand,
    1f to BrandBright,
    start = Offset.Zero,
    end = Offset.Infinite,
)

// Paskall's typefaces, as in the CMS: Outfit for display, Inter for everything else. Bundled as
// fixed weights cut from the CMS's own variable fonts (SIL Open Font License), so they work
// offline and on every Android version.
private val Outfit = FontFamily(Font(R.font.outfit_medium, FontWeight.Medium))
private val Inter = FontFamily(
    Font(R.font.inter_regular, FontWeight.Normal),
    Font(R.font.inter_medium, FontWeight.Medium),
)

/**
 * The pairing screen, in Paskall's own look — the first thing anyone setting up a screen sees:
 * the brand gradient, the logo in white, and the code on a translucent card. Deliberately the
 * app's error state too — a screen showing a code can be diagnosed from across a room, a black
 * one cannot. The server address is in the debug overlay, not here.
 */
@Composable
fun PairingScreen(code: String, error: String?) {
    Box(
        Modifier.fillMaxSize().background(BrandGradient),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            PaskallLogo(height = 44.dp)

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .padding(top = 36.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(Color.White.copy(alpha = 0.1f))
                    .border(1.dp, Color.White.copy(alpha = 0.18f), RoundedCornerShape(24.dp))
                    .padding(horizontal = 48.dp, vertical = 22.dp),
            ) {
                Text(
                    "Enter this code in the CMS",
                    color = OnBrandMuted,
                    fontSize = 22.sp,
                    fontFamily = Inter,
                )
                // Very large: this is read off a television from across a room.
                Text(
                    code,
                    color = Color.White,
                    fontSize = 116.sp,
                    fontFamily = Outfit,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 14.sp,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }

            // A live indicator, because a static code cannot be told apart from a frozen app.
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 28.dp),
            ) {
                PulsingDot()
                Text(
                    "Waiting for the CMS",
                    color = OnBrandMuted,
                    fontSize = 18.sp,
                    fontFamily = Inter,
                    modifier = Modifier.padding(start = 10.dp),
                )
            }

            if (error != null) {
                Text(
                    error,
                    color = OnBrandMuted,
                    fontSize = 16.sp,
                    fontFamily = Inter,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

/** The Paskall wordmark, in white for the brand gradient. */
@Composable
private fun PaskallLogo(height: Dp) {
    Image(
        painter = painterResource(R.drawable.paskall_wordmark),
        contentDescription = "Paskall",
        colorFilter = ColorFilter.tint(Color.White),
        modifier = Modifier.height(height),
    )
}

/** Slow pulse. Deliberately unhurried — this is ambient reassurance on a wall, not a spinner
 *  someone is waiting on. */
@Composable
private fun PulsingDot() {
    val transition = rememberInfiniteTransition(label = "pulse")
    val alpha by transition.animateFloat(
        initialValue = 0.25f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "alpha",
    )
    Box(
        Modifier
            .size(10.dp)
            .graphicsLayer { this.alpha = alpha }
            .background(InkInverse, CircleShape)
    )
}

/** Shown for a moment after a human claims the screen, so success is visible. */
@Composable
fun ClaimedScreen(deviceName: String) {
    Box(Modifier.fillMaxSize().background(Ink), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Connected", color = InkInverse, fontSize = 44.sp, fontWeight = FontWeight.Medium)
            Text(
                deviceName,
                color = InkMuted,
                fontSize = 22.sp,
                modifier = Modifier.padding(top = 10.dp),
            )
        }
    }
}

/** Downloading content before the first frame, with real progress — a large video over venue
 *  wifi takes long enough that a blank screen reads as broken. */
@Composable
fun PreparingScreen(deviceName: String, done: Int, total: Int, currentFile: String?) {
    Box(Modifier.fillMaxSize().background(Ink), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(horizontal = 64.dp),
        ) {
            Text(deviceName, color = InkInverse, fontSize = 34.sp, fontWeight = FontWeight.Medium)
            Text(
                "Preparing content",
                color = InkMuted,
                fontSize = 20.sp,
                modifier = Modifier.padding(top = 8.dp),
            )

            LinearProgressIndicator(
                progress = { if (total > 0) done.toFloat() / total else 0f },
                color = InkInverse,
                trackColor = InkMuted.copy(alpha = 0.3f),
                modifier = Modifier
                    .padding(top = 28.dp)
                    .fillMaxWidth(0.5f)
                    .height(4.dp),
            )
            Text(
                "$done of $total" + (currentFile?.let { " · $it" } ?: ""),
                color = InkSubtle,
                fontSize = 15.sp,
                modifier = Modifier.padding(top = 14.dp),
            )
        }
    }
}

/** Paired, but nothing assigned. A valid state for a new screen, not an error. */
@Composable
fun IdleScreen(deviceName: String) {
    Box(
        Modifier.fillMaxSize().background(Ink),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(deviceName, color = InkInverse, fontSize = 48.sp, fontWeight = FontWeight.Medium)
            Text(
                "No content assigned",
                color = InkMuted,
                fontSize = 22.sp,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}

/**
 * Paired, but the sync loop is failing. Deliberately verbose: this is read by whoever is
 * standing in front of a screen that is not showing what it should, and every line here is
 * something they would otherwise have to ask for.
 */
@Composable
fun TroubleScreen(deviceName: String?, message: String, apiHost: String, attempts: Int) {
    Box(Modifier.fillMaxSize().background(Ink), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(horizontal = 48.dp),
        ) {
            Text(
                deviceName ?: "This screen",
                color = InkInverse,
                fontSize = 34.sp,
                fontWeight = FontWeight.Medium,
            )
            Text(
                "Cannot reach the server",
                color = InkMuted,
                fontSize = 22.sp,
                modifier = Modifier.padding(top = 10.dp),
            )
            Text(
                apiHost,
                color = InkSubtle,
                fontSize = 16.sp,
                modifier = Modifier.padding(top = 22.dp),
            )
            Text(
                message,
                color = InkSubtle,
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 8.dp),
            )
            Text(
                "Retrying — attempt $attempts",
                color = InkMuted,
                fontSize = 15.sp,
                modifier = Modifier.padding(top = 22.dp),
            )
        }
    }
}

@Composable
fun StartingScreen() {
    Box(Modifier.fillMaxSize().background(BrandGradient), contentAlignment = Alignment.Center) {
        PaskallLogo(height = 44.dp)
    }
}

/**
 * A player update, as it happens, over whatever is on screen: a small card at the bottom with
 * the phase, a bar while the APK downloads, and the reason if it failed. The on-screen half of
 * the status the CMS shows for the same install — before this the only way to tell a download
 * crawling over bad wifi from one that had failed was to hold the corner for the debug overlay.
 * Deliberately small and low on the screen: content keeps playing behind it.
 */
@Composable
fun UpdateBanner(progress: UpdateProgress) {
    val title = when (progress.phase) {
        UpdatePhase.DOWNLOADING -> "Updating to ${progress.version}"
        UpdatePhase.INSTALLING -> "Installing ${progress.version}"
        UpdatePhase.FAILED -> "Update to ${progress.version} failed"
    }
    val detail = when (progress.phase) {
        UpdatePhase.DOWNLOADING -> {
            val pct = progress.percent?.let { "$it%" } ?: "Downloading"
            val size = progress.totalBytes?.let {
                " · %.1f of %.1f MB".format(progress.doneBytes / 1_048_576.0, it / 1_048_576.0)
            } ?: ""
            pct + size
        }
        UpdatePhase.INSTALLING -> "The player restarts by itself in a moment"
        UpdatePhase.FAILED -> progress.detail ?: "It will be retried shortly"
    }
    Box(Modifier.fillMaxSize().padding(28.dp), contentAlignment = Alignment.BottomCenter) {
        Column(
            modifier = Modifier
                .width(440.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xE6101111))
                .border(1.dp, Color.White.copy(alpha = 0.12f), RoundedCornerShape(16.dp))
                .padding(horizontal = 22.dp, vertical = 16.dp),
        ) {
            Text(
                title,
                color = if (progress.phase == UpdatePhase.FAILED) Color(0xFFFF8A80) else InkInverse,
                fontSize = 18.sp,
                fontFamily = Inter,
                fontWeight = FontWeight.Medium,
            )
            if (progress.phase == UpdatePhase.DOWNLOADING) {
                val pct = progress.percent
                if (pct != null) {
                    LinearProgressIndicator(
                        progress = { pct / 100f },
                        color = InkInverse,
                        trackColor = InkMuted.copy(alpha = 0.3f),
                        modifier = Modifier.padding(top = 12.dp).fillMaxWidth().height(4.dp),
                    )
                } else {
                    LinearProgressIndicator(
                        color = InkInverse,
                        trackColor = InkMuted.copy(alpha = 0.3f),
                        modifier = Modifier.padding(top = 12.dp).fillMaxWidth().height(4.dp),
                    )
                }
            }
            Text(
                detail,
                color = InkMuted,
                fontSize = 14.sp,
                fontFamily = Inter,
                modifier = Modifier.padding(top = 8.dp),
            )
        }
    }
}

/**
 * Hold the top-left corner to show this (see `MainActivity.dispatchTouchEvent`), or press Menu
 * on a keyboard. The only way to diagnose a screen you are standing in front of with no
 * keyboard and no logcat.
 */
@Composable
fun DebugOverlay(
    info: DebugInfo,
    onExitRequested: () -> Unit = {},
    onCheckUpdateRequested: () -> Unit = {},
) {
    Box(Modifier.fillMaxSize().background(Color(0xE6101111)), contentAlignment = Alignment.Center) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            DebugRow("device", info.deviceName ?: "—")
            DebugRow("api", info.apiBaseUrl)
            DebugRow("version", info.version?.take(24) ?: "—")
            DebugRow("items", info.itemCount.toString())
            DebugRow("cached", "%.1f MB".format(info.cachedBytes / 1_048_576.0))
            DebugRow("last poll", info.lastPoll)
            DebugRow("schedule", info.schedule ?: "default playlist")
            DebugRow("kiosk", info.kiosk)
            DebugRow("update", info.updateStatus ?: "not checked")
            DebugRow("last error", info.lastError ?: "none")
            Text(
                "Check for update",
                color = InkInverse,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier
                    .padding(top = 16.dp)
                    .clickable(onClick = onCheckUpdateRequested),
            )
            Text(
                "Exit kiosk",
                color = InkInverse,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier
                    .padding(top = 12.dp)
                    .clickable(onClick = onExitRequested),
            )
            Text(
                "Hold the top-left corner again to dismiss",
                color = InkMuted,
                fontSize = 14.sp,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

@Composable
private fun DebugRow(label: String, value: String) {
    Row2(label, value)
}

@Composable
private fun Row2(label: String, value: String) {
    androidx.compose.foundation.layout.Row {
        Text(label.padEnd(12), color = InkMuted, fontSize = 18.sp)
        Text(value, color = InkInverse, fontSize = 18.sp)
    }
}

/**
 * Gates "Exit kiosk" behind the CMS-configured PIN (`ManifestSettings.appPassword`).
 * `MainActivity` only shows this when a PIN is actually set — an unset PIN exits immediately,
 * with nothing to enter here.
 */
@Composable
fun ExitPinDialog(error: Boolean, onSubmit: (String) -> Unit, onDismiss: () -> Unit) {
    var pin by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Enter PIN to exit") },
        text = {
            Column {
                OutlinedTextField(
                    value = pin,
                    onValueChange = { pin = it },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                )
                if (error) {
                    Text(
                        "Incorrect PIN", color = Color(0xFFB3261E), fontSize = 13.sp,
                        modifier = Modifier.padding(top = 6.dp),
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = { onSubmit(pin) }) { Text("Exit") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
