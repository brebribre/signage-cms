import type { CSSProperties } from 'vue'

import type { SceneBackground } from '@/types/api'

/**
 * A scene's blurred background (models.playlist.SceneBackground on the backend): a blurred,
 * zoomed copy of the scene's largest picture or video fills whatever its elements don't cover.
 *
 * **Which element**: the biggest box by area, bottom-most on a tie; websites never. Every
 * renderer must pick the same one — this, the web player (web-player/src/ui/playback.ts) and
 * the Android player (PlaybackSurface.kt) — or the preview would promise a background the screen
 * doesn't show.
 */
export function blurSource<T extends { kind: string; width: number; height: number; zIndex: number }>(
  elements: T[],
): T | null {
  let best: T | null = null
  for (const el of elements) {
    if (el.kind !== 'image' && el.kind !== 'video') continue
    const area = el.width * el.height
    const bestArea = best ? best.width * best.height : -1
    if (area > bestArea || (area === bestArea && best && el.zIndex < best.zIndex)) best = el
  }
  return best
}

/** The picture to blur: the image itself, or a video's thumbnail — never a second copy of the
 *  playing video, which on a screen would need a second hardware decoder. */
export function blurImageUrl(el: { kind: string; url: string; thumbnailUrl: string | null }): string | null {
  return el.kind === 'image' ? el.url : el.thumbnailUrl
}

/** Blur is sized to the frame (container query units), so a small preview blurs exactly as
 *  much, proportionally, as a 4K panel does. The parent must be `container-type: size`. */
export const BLUR_IMAGE_STYLE: CSSProperties = {
  position: 'absolute',
  inset: '0',
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  filter: 'blur(3cqw) brightness(0.75)',
  transform: 'scale(1.15)',
}

export const SCENE_BACKGROUNDS: { value: SceneBackground; label: string; hint: string }[] = [
  { value: 'blur', label: 'Blurred', hint: 'A blurred copy of the largest picture or video (a video’s thumbnail) fills the screen behind the scene.' },
  { value: 'black', label: 'Black', hint: 'Plain black wherever the scene doesn’t cover the screen.' },
  { value: 'color', label: 'Colour', hint: 'A solid colour of your choice behind the scene.' },
]

/** The colour a scene starts with when Colour is picked — the brand blue. */
export const DEFAULT_BACKGROUND_COLOR = '#1D2FA5'

/** What actually paints behind a scene's elements: black, a colour, or (for blur) nothing —
 *  the blurred picture is drawn separately over a black frame. */
export function sceneBackdrop(background: SceneBackground, color: string | null | undefined): string {
  return background === 'color' && color ? color : '#000000'
}
