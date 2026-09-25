package com.fortu.player.playback

import com.fortu.player.api.ManifestElement

/**
 * The crop a Fill element carries from the CMS editor — which part of the picture shows in its
 * box — worked out exactly as the editor works it out, so a screen shows what the canvas shows.
 *
 * [resolveCropRect] is frontend/src/utils/cropMath.ts's, line for line (and web-player's
 * ui/crop.ts); keep the three the same. The editor resolves the window in the picture as it is
 * shown, turned by its rotation; a screen draws the file as stored inside a box that
 * `RotatedContent` then turns, so [fileRect] turns the window back into the file's coordinates.
 *
 * With no crop saved (all three null) this is a plain centred cover — what every screen showed
 * before, so scenes nobody cropped look exactly as they did.
 */

/** A rectangle as fractions of a picture: left, top, width, height. */
data class CropRect(val x: Float, val y: Float, val w: Float, val h: Float)

fun resolveCropRect(
    mediaWidth: Float,
    mediaHeight: Float,
    targetAspect: Float,
    cx: Float = 0.5f,
    cy: Float = 0.5f,
    zoom: Float = 1f,
): CropRect {
    val mediaAspect = mediaWidth / mediaHeight
    var w: Float
    var h: Float
    if (mediaAspect > targetAspect) {
        h = 1f
        w = targetAspect / mediaAspect
    } else {
        w = 1f
        h = mediaAspect / targetAspect
    }
    w = minOf(1f, w / maxOf(1f, zoom))
    h = minOf(1f, h / maxOf(1f, zoom))
    val clampedCx = minOf(maxOf(cx, w / 2), 1 - w / 2)
    val clampedCy = minOf(maxOf(cy, h / 2), 1 - h / 2)
    return CropRect(clampedCx - w / 2, clampedCy - h / 2, w, h)
}

/**
 * The part of the file, as fractions of the file as stored, that fills a box of
 * [innerWidth]×[innerHeight] — the box *before* it is turned by [rotation], which is how
 * `RotatedContent` lays an element out.
 */
fun fileRect(
    fileWidth: Float,
    fileHeight: Float,
    innerWidth: Float,
    innerHeight: Float,
    rotation: Int,
    cx: Float?,
    cy: Float?,
    zoom: Float?,
): CropRect {
    val swapped = rotation == 90 || rotation == 270
    val shownW = if (swapped) fileHeight else fileWidth
    val shownH = if (swapped) fileWidth else fileHeight
    val boxAspect = if (swapped) innerHeight / innerWidth else innerWidth / innerHeight
    val r = resolveCropRect(shownW, shownH, boxAspect, cx ?: 0.5f, cy ?: 0.5f, zoom ?: 1f)
    // Turning clockwise by 90° sends a file point (px, py) to (1 − py, px) on screen; 270° sends
    // it to (py, 1 − px); 180° to (1 − px, 1 − py). These are the inverses.
    return when (rotation) {
        90 -> CropRect(r.y, 1 - r.x - r.w, r.h, r.w)
        180 -> CropRect(1 - r.x - r.w, 1 - r.y - r.h, r.w, r.h)
        270 -> CropRect(1 - r.y - r.h, r.x, r.h, r.w)
        else -> r
    }
}

/** Whether the editor saved a crop for this element — anything but a plain centred cover. */
val ManifestElement.hasCrop: Boolean
    get() = fit == "cover" && (cropX != null || cropY != null || cropZoom != null)
