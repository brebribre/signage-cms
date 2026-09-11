package com.fortu.player.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fortu.player.DebugInfo

// Fortu's palette: near-black ink, off-white, mid grey. Same tokens as the CMS.
private val Ink = Color(0xFF101111)
private val InkInverse = Color(0xFFF9F9F9)
private val InkMuted = Color(0xFF7D7D7D)
private val InkSubtle = Color(0xFF4A4A4A)

/**
 * The pairing screen. Deliberately the app's error state too — a screen showing a code can be
 * diagnosed from across a room, a black one cannot.
 */
@Composable
fun PairingScreen(code: String, apiHost: String, error: String?, checks: Int) {
    Box(
        Modifier.fillMaxSize().background(Ink),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                "FORTU",
                color = InkInverse,
                fontSize = 28.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 6.sp,
            )
            Text(
                "Enter this code in the CMS",
                color = InkMuted,
                fontSize = 22.sp,
                modifier = Modifier.padding(top = 40.dp),
            )
            // Very large: this is read off a television from across a room.
            Text(
                code,
                color = InkInverse,
                fontSize = 120.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 16.sp,
                modifier = Modifier.padding(top = 16.dp),
            )

            // A live indicator, because a static code cannot be told apart from a frozen app.
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 24.dp),
            ) {
                PulsingDot()
                Text(
                    if (checks == 0) "Waiting for the CMS" else "Waiting for the CMS · checked ${checks}×",
                    color = InkMuted,
                    fontSize = 16.sp,
                    modifier = Modifier.padding(start = 10.dp),
                )
            }

            // The single most useful line when pairing "does not work": almost always the
            // screen and the CMS are pointed at different servers, and this is the only place
            // that is visible without a laptop.
            Text(
                apiHost,
                color = InkSubtle,
                fontSize = 14.sp,
                modifier = Modifier.padding(top = 28.dp),
            )

            if (error != null) {
                Text(
                    error,
                    color = InkMuted,
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        }
    }
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
    Box(Modifier.fillMaxSize().background(Ink), contentAlignment = Alignment.Center) {
        Text("FORTU", color = InkInverse, fontSize = 28.sp, letterSpacing = 6.sp)
    }
}

/**
 * Long-press anywhere to show this. The only way to diagnose a screen you are standing in
 * front of with no keyboard and no logcat.
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
                "Long-press again to dismiss",
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
