import type { CSSProperties } from 'vue'

/** Swaps width/height for a 90°/270° rotation — "rotate the video upright first, then
 *  crop/fit the corrected orientation" is the whole rotation feature in one function. Every
 *  aspect-ratio computation downstream (resolveCropRect, or a plain object-fit box for
 *  Contain/Stretch) should use these effective dimensions, never the raw media ones, once a
 *  rotation is in play. */
export function effectiveDimensions(
  width: number,
  height: number,
  rotationDegrees: number,
): { width: number; height: number } {
  return rotationDegrees === 90 || rotationDegrees === 270
    ? { width: height, height: width }
    : { width, height }
}

export interface CropRect {
  /** Normalized [0,1] top-left of the visible crop, in the media's own 0-1 space. */
  x: number
  y: number
  /** Normalized [0,1] size of the visible crop. */
  w: number
  h: number
}

/**
 * Resolves a stored (center, zoom) crop into an actual rectangle for a given target aspect
 * ratio — the one function both the placement editor and every renderer share, so editing and
 * playback can never disagree.
 *
 * `zoom` is relative to the *target* aspect ratio's own tightest "cover" fit, not an absolute
 * magnification: the same `zoom=1.3` crops a different absolute fraction of the image on a 9:16
 * target than on a 16:9 one. That is intentional — it is "zoom further into whatever is already
 * cover-fit for this device", the same way plain `object-fit: cover` already varies its crop
 * per aspect ratio with zero stored state at `zoom=1`.
 *
 * `cx`/`cy` are clamped back inside the image's bounds for whatever rectangle size results, so
 * a crop authored against one aspect ratio still resolves to something sane against a very
 * different one — sliding the window back onto the image rather than sampling outside it.
 */
export function resolveCropRect(
  mediaWidth: number,
  mediaHeight: number,
  targetAspect: number,
  cx = 0.5,
  cy = 0.5,
  zoom = 1,
): CropRect {
  const mediaAspect = mediaWidth / mediaHeight
  let w: number
  let h: number
  if (mediaAspect > targetAspect) {
    h = 1
    w = targetAspect / mediaAspect
  } else {
    w = 1
    h = mediaAspect / targetAspect
  }
  w = Math.min(1, w / Math.max(1, zoom))
  h = Math.min(1, h / Math.max(1, zoom))

  const clampedCx = Math.min(Math.max(cx, w / 2), 1 - w / 2)
  const clampedCy = Math.min(Math.max(cy, h / 2), 1 - h / 2)

  return { x: clampedCx - w / 2, y: clampedCy - h / 2, w, h }
}

/** `resolveCropRect`, expressed as CSS percentages for absolute positioning a media element
 *  that is itself sized to the *full* media (not the crop) inside an `overflow: hidden` box.
 *
 *  `maxWidth`/`maxHeight: 'none'` are load-bearing, not decoration: Tailwind's preflight resets
 *  `img`/`video` to `max-width: 100%; height: auto`, which silently caps this element at its
 *  container's own size — the zoomed-in width this function computes (routinely >100%) gets
 *  clamped right back down, and every crop renders as "mostly the container's background,
 *  barely any image." Confirmed live: without this, both the placement editor and the main
 *  screen preview showed a nearly-black frame with only a sliver of the media visible. */
export function cropRectToStyle(rect: CropRect): {
  left: string
  top: string
  width: string
  height: string
  maxWidth: string
  maxHeight: string
} {
  return {
    left: `${(-rect.x / rect.w) * 100}%`,
    top: `${(-rect.y / rect.h) * 100}%`,
    width: `${(1 / rect.w) * 100}%`,
    height: `${(1 / rect.h) * 100}%`,
    maxWidth: 'none',
    maxHeight: 'none',
  }
}

/** Style for the wrapper a rotated video/image sits inside — needs `container-type: size` so
 *  `rotationStyle()`'s `cqw`/`cqh` units below resolve against *this* element's own box, not
 *  the page. Apply on top of whatever already positions the wrapper itself (cropRectToStyle's
 *  percentages for Fill, or a plain inset/aspect-ratio box for Contain/Stretch). */
export const ROTATION_WRAPPER_STYLE = { containerType: 'size' } as const

/**
 * Style for the innermost, actually-rotated video/image element — the only thing in the
 * whole crop/rotate system that ever gets a `transform`.
 *
 * The geometry (verified numerically, not guessed): a WxH box, rotated N° around its own
 * center and sized via `cqw`/`cqh` (1% of ROTATION_WRAPPER_STYLE's own box, swapped for
 * 90°/270°) rather than plain `%`, exactly fills a wrapper sized to the swapped aspect ratio
 * — with zero JS pixel measurement. At 0°/180° there's no swap, so this degrades to exactly
 * the old unrotated centered-fill behavior.
 */
export function rotationStyle(rotationDegrees: number): CSSProperties {
  const swap = rotationDegrees === 90 || rotationDegrees === 270
  return {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: swap ? '100cqh' : '100cqw',
    height: swap ? '100cqw' : '100cqh',
    maxWidth: 'none',
    maxHeight: 'none',
    transform: `translate(-50%, -50%) rotate(${rotationDegrees}deg)`,
  }
}
