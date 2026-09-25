package com.fortu.player.kiosk

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Working out how a screen is mounted, as the CMS's orientation value ("0", "90", "180", "270"),
 * so pairing needn't ask. Plain Kotlin, no Android, so every case is pinned by a unit test;
 * [MountDetector] feeds it what the device reports.
 *
 * Two sources, in order:
 * 1. **Gravity.** A screen with a motion sensor knows which edge points down. That is the
 *    physical truth, whatever the software is set to.
 * 2. **The display's own rotation.** With no usable reading, a display someone has set to a
 *    rotation (or a panel that is portrait by nature) is taken at its word.
 * Otherwise null: a TV box has no sensor, and the TV it drives reports landscape however it
 * hangs, so only a person can say — and the CMS asks.
 *
 * The CMS value is not a raw angle on Android. The player turns it into one of Android's four
 * screen orientations (MainActivity: "0" landscape, "90" portrait, "180" reverse landscape,
 * "270" reverse portrait), and which physical rotation each of those means depends on the
 * device — a tablet and a phone disagree about "portrait", and some makers reverse it. So the
 * answer here is whichever of the four lands the display on the rotation that is upright.
 */

/**
 * How far the device is tilted from its natural position, in degrees, exactly as Android's
 * `OrientationEventListener` works it out: 0 upright, 90 with its left side at the top, 180
 * upside down, 270 with its right side at the top. [ax], [ay], [az] are an accelerometer or
 * gravity reading on the device's own axes. Null when it lies (nearly) flat.
 */
fun tiltDegrees(ax: Float, ay: Float, az: Float): Int? {
    val x = -ax
    val y = -ay
    val z = -az
    if (4 * (x * x + y * y) < z * z) return null
    val angle = Math.toDegrees(atan2(-y.toDouble(), x.toDouble()))
    return (((90 - angle.roundToInt()) % 360) + 360) % 360
}

/** The nearest quarter turn, but only when the tilt is clearly near one — within [tolerance]
 *  degrees — so a screen leaning half-way between two is not guessed at. */
fun nearestQuarter(degrees: Int, tolerance: Int = 30): Int? {
    val quarter = ((degrees + 45) / 90 * 90) % 360
    val off = abs(degrees - quarter).let { min(it, 360 - it) }
    return if (off <= tolerance) quarter else null
}

/** The display rotation (Android's `Surface.ROTATION_*`, in degrees) that shows content upright
 *  on a device tilted by [tilt]: turned the other way by the same amount. */
fun uprightRotation(tilt: Int): Int = (360 - tilt) % 360

/**
 * The CMS value whose Android screen orientation puts the display at [rotation] degrees, on a
 * device that is landscape (or portrait) by nature and may reverse the default — AOSP's
 * `DisplayRotation`, which decides what "portrait" and "reverse landscape" mean on each device.
 */
fun orientationForRotation(rotation: Int, naturalLandscape: Boolean, reverseDefault: Boolean): String? {
    val byRotation: Map<Int, String> = if (naturalLandscape) {
        mapOf(
            0 to "0",
            180 to "180",
            (if (reverseDefault) 90 else 270) to "90",
            (if (reverseDefault) 270 else 90) to "270",
        )
    } else {
        mapOf(
            0 to "90",
            180 to "270",
            (if (reverseDefault) 270 else 90) to "0",
            (if (reverseDefault) 90 else 270) to "180",
        )
    }
    return byRotation[rotation]
}

/**
 * The CMS orientation for this screen, or null when it can't tell.
 *
 * [tilt] is [tiltDegrees] from a fresh sensor reading, or null with no sensor or lying flat;
 * [displayRotation] the display's current rotation in degrees.
 */
fun detectOrientation(tilt: Int?, displayRotation: Int, naturalLandscape: Boolean, reverseDefault: Boolean): String? {
    tilt?.let(::nearestQuarter)?.let { quarter ->
        return orientationForRotation(uprightRotation(quarter), naturalLandscape, reverseDefault)
    }
    // No sensor to go by. A landscape panel at its default rotation is the one case we can't
    // read: most are landscape, but a TV hung sideways looks exactly the same from here.
    if (naturalLandscape && displayRotation == 0) return null
    return orientationForRotation(displayRotation, naturalLandscape, reverseDefault)
}
