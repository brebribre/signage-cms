package com.fortu.player

import com.fortu.player.kiosk.detectOrientation
import com.fortu.player.kiosk.nearestQuarter
import com.fortu.player.kiosk.orientationForRotation
import com.fortu.player.kiosk.tiltDegrees
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** How a screen works out its own mounting — see kiosk/Mount.kt. A wrong answer here shows a
 *  totem's content upside down, so every case is pinned. */
class MountTest {
    private val g = 9.81f

    @Test fun tiltMatchesOrientationEventListener() {
        assertEquals(0, tiltDegrees(0f, g, 0f))      // upright in its natural position
        assertEquals(90, tiltDegrees(-g, 0f, 0f))    // left side at the top
        assertEquals(180, tiltDegrees(0f, -g, 0f))   // upside down
        assertEquals(270, tiltDegrees(g, 0f, 0f))    // right side at the top
        assertNull(tiltDegrees(0.5f, 0.5f, g))       // lying flat
    }

    @Test fun onlyClearQuarterTurnsCount() {
        assertEquals(0, nearestQuarter(355))
        assertEquals(90, nearestQuarter(110))
        assertNull(nearestQuarter(135))              // half-way between two: don't guess
    }

    @Test fun landscapeTabletRotationsMapToTheCmsValues() {
        // Landscape by nature, AOSP default: portrait is ROTATION_270.
        assertEquals("0", orientationForRotation(0, naturalLandscape = true, reverseDefault = false))
        assertEquals("90", orientationForRotation(270, naturalLandscape = true, reverseDefault = false))
        assertEquals("180", orientationForRotation(180, naturalLandscape = true, reverseDefault = false))
        assertEquals("270", orientationForRotation(90, naturalLandscape = true, reverseDefault = false))
        // A maker that reverses it.
        assertEquals("90", orientationForRotation(90, naturalLandscape = true, reverseDefault = true))
    }

    @Test fun portraitPanelRotationsMapToTheCmsValues() {
        assertEquals("90", orientationForRotation(0, naturalLandscape = false, reverseDefault = false))
        assertEquals("0", orientationForRotation(90, naturalLandscape = false, reverseDefault = false))
        assertEquals("270", orientationForRotation(180, naturalLandscape = false, reverseDefault = false))
        assertEquals("180", orientationForRotation(270, naturalLandscape = false, reverseDefault = false))
    }

    @Test fun gravityDecidesWhenThereIsAReading() {
        // A landscape tablet stood with its left side up needs the display at ROTATION_270,
        // which is its "portrait" — the CMS's 90.
        assertEquals("90", detectOrientation(tiltDegrees(-g, 0f, 0f), 0, true, false))
        assertEquals("270", detectOrientation(tiltDegrees(g, 0f, 0f), 0, true, false))
        assertEquals("0", detectOrientation(tiltDegrees(0f, g, 0f), 90, true, false))
    }

    @Test fun withoutAReadingTheDisplayRotationIsUsedUnlessItCantTell() {
        assertNull(detectOrientation(null, 0, naturalLandscape = true, reverseDefault = false))
        assertEquals("90", detectOrientation(null, 270, naturalLandscape = true, reverseDefault = false))
        assertEquals("90", detectOrientation(null, 0, naturalLandscape = false, reverseDefault = false))
        // Lying flat is no reading at all.
        assertNull(detectOrientation(tiltDegrees(0f, 0f, g), 0, true, false))
    }
}
