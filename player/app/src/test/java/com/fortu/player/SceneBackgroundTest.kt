package com.fortu.player

import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestSlot
import com.fortu.player.playback.SceneBackground
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** The same rule, and the same cases, as the CMS preview and the web player. */
class SceneBackgroundTest {
    private fun el(id: String, kind: String, width: Float = 1f, height: Float = 1f) =
        ManifestElement(id = id, kind = kind, url = id, checksum = id, bytes = 1, width = width, height = height)

    @Test
    fun `a black scene has no blurred background`() {
        assertNull(SceneBackground.blurSource(ManifestSlot("s", 5, listOf(el("a", "image")))))
    }

    @Test
    fun `the biggest box wins, bottom-most on a tie, never a website`() {
        val slot = ManifestSlot(
            "s", 5,
            listOf(el("web", "web"), el("small", "image", 0.2f, 0.2f), el("big", "video", 0.5f, 0.9f), el("tie", "image", 0.9f, 0.5f)),
            background = "blur",
        )
        assertEquals("big", SceneBackground.blurSource(slot)?.id)
    }
}
