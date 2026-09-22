package com.fortu.player.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate

/**
 * The turn to draw, in degrees clockwise from the panel's own landscape, for the CMS's
 * orientation value ("0"/"90"/"180"/"270", or the older "landscape"/"portrait" words). Null,
 * before the first manifest, is 0.
 */
fun rotationDegrees(orientation: String?): Int = when (orientation) {
    "90", "portrait" -> 90
    "180" -> 180
    "270" -> 270
    else -> 0
}

/**
 * Draws [content] turned by [degrees] to fill the window: for 90°/270° it is measured at the
 * window's height-by-width (a portrait canvas lying inside the landscape window) and rotated
 * into place, so every scene, the pairing code and the idle card read upright on a portrait
 * totem driven by hardware that cannot rotate. Pointer input follows the rotation, so a
 * touchscreen keeps working. 0° is a plain pass-through with no extra layer.
 */
@Composable
fun SelfRotatingStage(degrees: Int, content: @Composable () -> Unit) {
    if (degrees == 0) {
        content()
        return
    }
    val swapped = degrees == 90 || degrees == 270
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val contentWidth = if (swapped) maxHeight else maxWidth
        val contentHeight = if (swapped) maxWidth else maxHeight
        Box(
            Modifier
                .align(Alignment.Center)
                // requiredSize: for a 90°/270° turn the content's width is the window's height,
                // which `size` would coerce back down to the window's width.
                .requiredSize(contentWidth, contentHeight)
                .rotate(degrees.toFloat()),
        ) {
            content()
        }
    }
}
