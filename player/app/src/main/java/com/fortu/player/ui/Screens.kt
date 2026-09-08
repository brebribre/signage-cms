package com.fortu.player.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fortu.player.DebugInfo

// Fortu's palette: near-black ink, off-white, mid grey. Same tokens as the CMS.
private val Ink = Color(0xFF101111)
private val InkInverse = Color(0xFFF9F9F9)
private val InkMuted = Color(0xFF7D7D7D)

/**
 * The pairing screen. Deliberately the app's error state too — a screen showing a code can be
 * diagnosed from across a room, a black one cannot.
 */
@Composable
fun PairingScreen(code: String, error: String?) {
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
            if (error != null) {
                Text(
                    error,
                    color = InkMuted,
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 32.dp),
                )
            }
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
fun DebugOverlay(info: DebugInfo) {
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
            DebugRow("last error", info.lastError ?: "none")
            Text(
                "Long-press again to dismiss",
                color = InkMuted,
                fontSize = 14.sp,
                modifier = Modifier.padding(top = 16.dp),
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
