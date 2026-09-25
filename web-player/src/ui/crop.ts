/**
 * The crop a Fill element carries from the CMS editor — which part of the picture shows in its
 * box — worked out exactly as the editor works it out, so a screen shows what the canvas shows.
 *
 * `resolveCropRect` is a copy of frontend/src/utils/cropMath.ts's, line for line; keep the two
 * the same. The editor resolves the window in the picture as it is shown (turned by its
 * rotation); a screen draws the file as stored inside a box that is then turned, so `fileRect`
 * turns the window back into the file's own coordinates.
 *
 * With no crop saved (all three null) this is a plain centred cover — what every screen showed
 * before, so scenes nobody cropped look exactly as they did.
 */

/** A rectangle as fractions of a picture: left, top, width, height. */
export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export function resolveCropRect(
  mediaWidth: number,
  mediaHeight: number,
  targetAspect: number,
  cx = 0.5,
  cy = 0.5,
  zoom = 1,
): Rect {
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

export interface CropSpec {
  cropX?: number | null
  cropY?: number | null
  cropZoom?: number | null
  rotation: number
}

/**
 * The part of the file, as fractions of the file as stored, that fills a box of `innerW`×`innerH`
 * — the box *before* it is turned by `rotation`, which is how the players lay an element out.
 */
export function fileRect(fileW: number, fileH: number, innerW: number, innerH: number, spec: CropSpec): Rect {
  const swapped = spec.rotation === 90 || spec.rotation === 270
  // What the editor saw: the picture turned, in the box as it appears on screen.
  const shownW = swapped ? fileH : fileW
  const shownH = swapped ? fileW : fileH
  const boxAspect = swapped ? innerH / innerW : innerW / innerH
  const r = resolveCropRect(shownW, shownH, boxAspect, spec.cropX ?? 0.5, spec.cropY ?? 0.5, spec.cropZoom ?? 1)
  // Back into the file's own coordinates. Turning clockwise by 90° sends a file point (px, py)
  // to (1 − py, px) on screen; 270° sends it to (py, 1 − px); 180° to (1 − px, 1 − py).
  switch (spec.rotation) {
    case 90: return { x: r.y, y: 1 - r.x - r.w, w: r.h, h: r.w }
    case 180: return { x: 1 - r.x - r.w, y: 1 - r.y - r.h, w: r.w, h: r.h }
    case 270: return { x: 1 - r.y - r.h, y: r.x, w: r.h, h: r.w }
    default: return r
  }
}

/** Absolute placement for an `<img>` or `<video>` so that `rect` of it exactly fills a box of
 *  `innerW`×`innerH`; the element's box (`.el`, overflow hidden) cuts off the rest. */
export function cropStyle(rect: Rect, innerW: number, innerH: number): Partial<CSSStyleDeclaration> {
  const width = innerW / rect.w
  const height = innerH / rect.h
  return {
    position: 'absolute',
    left: `${-rect.x * width}px`,
    top: `${-rect.y * height}px`,
    width: `${width}px`,
    height: `${height}px`,
    maxWidth: 'none',
    maxHeight: 'none',
    objectFit: 'fill',
  }
}
