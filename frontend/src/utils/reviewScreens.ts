import type { DeviceRead, DeviceOrientation, ReviewRead } from '@/types/api'
import { isPortrait } from '@/utils/orientation'

/** A screen a review can be previewed on: the size its content is laid out at. `reported` is
 *  false when the screen never told us its resolution, and a Full HD canvas of its orientation
 *  stands in. */
export interface PreviewScreen {
  id: string
  name: string
  width: number
  height: number
  reported: boolean
}

function sized(id: string, name: string, orientation: DeviceOrientation, width: number | null, height: number | null): PreviewScreen {
  if (width && height) return { id, name, width, height, reported: true }
  return isPortrait(orientation)
    ? { id, name, width: 1080, height: 1920, reported: false }
    : { id, name, width: 1920, height: 1080, reported: false }
}

/**
 * The screens a review's preview offers — only the ones the change reaches.
 *
 * From what the review saved when it was sent (`screen_specs`), so a screen deleted or turned
 * since still previews at the shape it had. Reviews sent before that was saved have only names:
 * those are matched against the screens that still exist, and a name that matches none is still
 * offered, at Full HD landscape, rather than dropped.
 */
export function reviewScreens(review: ReviewRead, devices: DeviceRead[]): PreviewScreen[] {
  if (review.screen_specs?.length) {
    return review.screen_specs.map((s) => sized(s.id, s.name, s.orientation, s.width, s.height))
  }
  return review.screens.map((name, i) => {
    const d = devices.find((x) => x.name === name)
    if (!d) return sized(`name-${i}`, name, '0', null, null)
    const long = Math.max(d.screen_width ?? 0, d.screen_height ?? 0)
    const short = Math.min(d.screen_width ?? 0, d.screen_height ?? 0)
    const portrait = isPortrait(d.orientation)
    return long && short
      ? sized(d.id, d.name, d.orientation, portrait ? short : long, portrait ? long : short)
      : sized(d.id, d.name, d.orientation, null, null)
  })
}
