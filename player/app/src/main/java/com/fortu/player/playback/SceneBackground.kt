package com.fortu.player.playback

import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestSlot

/**
 * A scene's blurred background: a blurred, zoomed copy of the scene's largest picture or video
 * fills whatever its elements don't cover.
 *
 * **Which element**: the biggest box by area, bottom-most on a tie (elements arrive bottom-first),
 * websites never — the same rule as the CMS preview (frontend/src/utils/sceneBackground.ts) and
 * the web player (web-player/src/sceneBackground.ts), so the screen shows what the editor promised.
 *
 * Pure, so it is tested on a plain JVM (SceneBackgroundTest).
 */
object SceneBackground {
    const val BLUR = "blur"

    fun blurSource(slot: ManifestSlot): ManifestElement? {
        if (slot.background != BLUR) return null
        var best: ManifestElement? = null
        var bestArea = -1f
        for (element in slot.elements) {
            if (element.kind != "image" && element.kind != "video") continue
            val area = element.width * element.height
            if (area > bestArea) {
                best = element
                bestArea = area
            }
        }
        return best
    }
}
