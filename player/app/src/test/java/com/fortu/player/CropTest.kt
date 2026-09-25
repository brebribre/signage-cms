package com.fortu.player

import com.fortu.player.playback.fileRect
import com.fortu.player.playback.resolveCropRect
import org.junit.Assert.assertEquals
import org.junit.Test

/** The crop maths, pinned to the same cases as web-player/src/ui/crop.test.ts — the CMS editor,
 *  the web player and this player must resolve the same window. */
class CropTest {
    private fun close(expected: Float, actual: Float) = assertEquals(expected, actual, 1e-5f)

    @Test fun noCropIsCentredCover() {
        val r = resolveCropRect(4000f, 3000f, 16f / 9f)
        close(0f, r.x); close(1f, r.w)
        close((4f / 3f) / (16f / 9f), r.h); close((1 - r.h) / 2, r.y)
    }

    @Test fun pannedWindowStaysOnThePicture() {
        val r = resolveCropRect(1000f, 1000f, 1f, 0f, 1f, 2f)
        close(0f, r.x); close(0.5f, r.y); close(0.5f, r.w); close(0.5f, r.h)
    }

    @Test fun unturnedIsTheResolvedWindow() {
        val r = fileRect(1920f, 1080f, 800f, 450f, 0, 0.3f, 0.4f, 2f)
        assertEquals(resolveCropRect(1920f, 1080f, 800f / 450f, 0.3f, 0.4f, 2f), r)
    }

    @Test fun turnedWindowLandsOnTheSamePixels() {
        for (rotation in listOf(90, 180, 270)) {
            val fileW = 3000f
            val fileH = 2000f
            val swapped = rotation == 90 || rotation == 270
            val innerW = 600f
            val innerH = 900f
            val shown = resolveCropRect(
                if (swapped) fileH else fileW, if (swapped) fileW else fileH,
                if (swapped) innerH / innerW else innerW / innerH, 0.35f, 0.6f, 1.5f,
            )
            val r = fileRect(fileW, fileH, innerW, innerH, rotation, 0.35f, 0.6f, 1.5f)
            close(shown.w * shown.h, r.w * r.h)
            close(innerW / innerH, (r.w * fileW) / (r.h * fileH))
            val px = r.x + r.w / 2
            val py = r.y + r.h / 2
            val onScreen = when (rotation) {
                90 -> Pair(1 - py, px)
                180 -> Pair(1 - px, 1 - py)
                else -> Pair(py, 1 - px)
            }
            close(shown.x + shown.w / 2, onScreen.first)
            close(shown.y + shown.h / 2, onScreen.second)
        }
    }
}
