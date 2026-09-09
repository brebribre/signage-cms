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
 *  that is itself sized to the *full* media (not the crop) inside an `overflow: hidden` box. */
export function cropRectToStyle(rect: CropRect): {
  left: string
  top: string
  width: string
  height: string
} {
  return {
    left: `${(-rect.x / rect.w) * 100}%`,
    top: `${(-rect.y / rect.h) * 100}%`,
    width: `${(1 / rect.w) * 100}%`,
    height: `${(1 / rect.h) * 100}%`,
  }
}
