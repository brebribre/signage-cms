import type { ManifestElement, ManifestSlot } from './api'

/**
 * A scene's blurred background: a blurred, zoomed copy of the scene's largest picture or video
 * fills whatever its elements don't cover.
 *
 * **Which element**: the biggest box by area, bottom-most on a tie (elements arrive bottom-first),
 * websites never — the same rule as the CMS preview (frontend/src/utils/sceneBackground.ts) and
 * the Android player, so the screen shows what the editor promised.
 */
export function blurSource(slot: ManifestSlot): ManifestElement | null {
  if (slot.background !== 'blur') return null
  let best: ManifestElement | null = null
  let bestArea = -1
  for (const el of slot.elements) {
    if (el.kind !== 'image' && el.kind !== 'video') continue
    const area = (el.width ?? 1) * (el.height ?? 1)
    if (area > bestArea) {
      best = el
      bestArea = area
    }
  }
  return best
}

/** Where a video's thumbnail lives among the stored files and sources, beside the video's own. */
export const posterKey = (element: ManifestElement) => `poster:${element.checksum}`
