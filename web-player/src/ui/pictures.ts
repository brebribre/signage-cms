/**
 * Pictures rendered ahead of time, at the size they will be shown, and blurred backgrounds
 * rendered once — the two things a TV browser cannot do on the fly without a visible hitch.
 *
 * Why not just `<img>`: a phone photo is 12 megapixels. Shown through an `<img>` the browser
 * decodes it as the slot appears, uploads the whole thing to the GPU as a texture, and then
 * composites that texture through every frame of the crossfade — on a TV's GPU that is the
 * stutter people see at every transition. Drawn once into a canvas the size of its box it is a
 * 2-megapixel texture, decoded before the slot is due, and the fade is two flat layers.
 *
 * Why not `filter: blur()`: a 60px blur over a full-screen image is re-rendered by the GPU on
 * every frame it is on screen, fade included; on a TV that alone can halve the frame rate. The
 * blur here is a scale-down to a few dozen pixels and the browser's own smoothing on the way
 * back up — computed once, then a plain small texture.
 *
 * Every function degrades: no canvas support, a picture that will not decode, a tainted draw —
 * the caller falls back to the `<img>` path (see playback.ts), which is what the player did
 * before this file existed.
 */

import { type CropSpec, fileRect } from './crop'

export interface Box {
  width: number
  height: number
}

export type Fit = 'contain' | 'cover' | 'fill'

/** The largest canvas side we ask for. A TV browser that is short of GPU memory fails to paint
 *  a bigger one silently, and nothing on a wall needs more than this. */
const MAX_CANVAS_SIDE = 4096
/** The blurred background is rendered at the stage's size divided by this. Six keeps the
 *  texture tiny (320×180 on a 1080p wall) while the browser's final stretch stays small
 *  enough to look smooth: a TV browser upscales with plain bilinear filtering, and at twenty
 *  times — the first version's 96-pixel canvas — bilinear shows as blocks. */
const BLUR_DOWNSCALE = 6
/** The blur radius as a share of the stage width — the same 3% the CSS filter used. */
const BLUR_RADIUS_FRACTION = 0.03
/** Dim, so the scene in front stands out — the same 0.75 as the `brightness()` it replaces. */
const BLUR_DIM = 0.25

export function canvasSupported(): boolean {
  try {
    return !!document.createElement('canvas').getContext('2d')
  } catch {
    return false
  }
}

/** Decoded and ready to draw, or rejected. `decode()` is preferred, since it does the work off
 *  the main thread; a browser without it, or one that refuses it for a cross-origin file, still
 *  fires `load`, after which drawing decodes synchronously — once, ahead of time, here. */
export function loadImage(url: string): Promise<HTMLImageElement> {
  const img = new Image()
  img.decoding = 'async'
  const loaded = new Promise<HTMLImageElement>((resolve, reject) => {
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image failed to load'))
  })
  img.src = url
  if (typeof img.decode !== 'function') return loaded
  return img.decode().then(() => img, () => loaded)
}

/** Source and destination rectangles for `fit` — the same rule as CSS object-fit, so the picture
 *  lands exactly where the `<img>` path would have put it. */
export function fitRects(image: Box, box: Box, fit: Fit) {
  if (fit === 'fill') {
    return { sx: 0, sy: 0, sw: image.width, sh: image.height, dx: 0, dy: 0, dw: box.width, dh: box.height }
  }
  const scale = fit === 'cover'
    ? Math.max(box.width / image.width, box.height / image.height)
    : Math.min(box.width / image.width, box.height / image.height)
  const dw = image.width * scale
  const dh = image.height * scale
  return {
    sx: 0, sy: 0, sw: image.width, sh: image.height,
    dx: (box.width - dw) / 2, dy: (box.height - dh) / 2, dw, dh,
  }
}

/** The pixel size a canvas gets for a CSS box: the device's own pixels up to a cap, so a 4K
 *  panel that reports 1920 CSS pixels still gets a sharp picture. */
export function canvasSize(box: Box): Box {
  const dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1))
  const scale = Math.min(dpr, MAX_CANVAS_SIDE / Math.max(1, box.width, box.height))
  return { width: Math.max(1, Math.round(box.width * scale)), height: Math.max(1, Math.round(box.height * scale)) }
}

/** Draws `url` into `canvas`, fitted to `box`. Resolves when the picture is on the canvas;
 *  rejects if it never loads or cannot be drawn. The canvas may already be on screen —
 *  transparent until this lands, like an `<img>` before its first paint.
 *
 *  A cover (Fill) picture with `crop` draws exactly the window the CMS editor showed — see
 *  ui/crop.ts — which with no crop saved is the same centred cover as before. */
export async function paintPicture(canvas: HTMLCanvasElement, url: string, box: Box, fit: Fit, crop?: PictureCrop): Promise<void> {
  const img = await loadImage(url)
  const size = canvasSize(box)
  canvas.width = size.width
  canvas.height = size.height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no 2d context')
  const natural = { width: img.naturalWidth, height: img.naturalHeight }
  if (fit === 'cover' && crop) {
    const r = fileRect(crop.fileWidth ?? natural.width, crop.fileHeight ?? natural.height, box.width, box.height, crop)
    ctx.drawImage(img, r.x * natural.width, r.y * natural.height, r.w * natural.width, r.h * natural.height, 0, 0, size.width, size.height)
    return
  }
  const r = fitRects(natural, size, fit)
  ctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, r.dx, r.dy, r.dw, r.dh)
}

/** What paintPicture needs to draw a cropped Fill picture: the crop, and the file's stored size
 *  when the manifest has it (the decoded size otherwise). */
export interface PictureCrop extends CropSpec {
  fileWidth?: number | null
  fileHeight?: number | null
}

/** Whether this browser's canvas can blur while drawing (`ctx.filter`, Chromium 52+). Checked
 *  on a real context, since some TV browsers expose the property and ignore it. */
function canvasFilterSupported(ctx: CanvasRenderingContext2D): boolean {
  if (!('filter' in ctx)) return false
  try {
    ctx.filter = 'blur(1px)'
    const ok = ctx.filter !== 'none' && ctx.filter !== ''
    ctx.filter = 'none'
    return ok
  } catch {
    return false
  }
}

/** Draws a blurred, dimmed, cover-fitted copy of `url` into `canvas`, at a sixth of the stage's
 *  size, blurred for real at that size — once. CSS then stretches it to the stage, and a
 *  six-times stretch of an already-smooth picture stays smooth on a TV's bilinear scaler.
 *
 *  The blur itself is the canvas's own `filter` where the browser has it (one draw), and
 *  otherwise a pyramid: three bilinear passes down and back up, each of which smooths — the
 *  approximation every image library reaches for when there is no Gaussian to hand. Either way
 *  the source is drawn a blur-radius larger than the canvas on every side, so the blur's soft
 *  edges fall outside it rather than fading to black at the screen's border. */
export async function paintBlur(canvas: HTMLCanvasElement, url: string, stage: Box): Promise<void> {
  const img = await loadImage(url)
  const aspect = stage.width / Math.max(1, stage.height)
  const w = Math.max(64, Math.round(stage.width / BLUR_DOWNSCALE))
  const h = Math.max(1, Math.round(w / aspect))
  const radius = Math.max(2, Math.round(w * BLUR_RADIUS_FRACTION))
  const image = { width: img.naturalWidth, height: img.naturalHeight }

  // Cover-fit into a working canvas overscanned by the radius on every side.
  const over = { width: w + radius * 2, height: h + radius * 2 }
  const work = document.createElement('canvas')
  work.width = over.width
  work.height = over.height
  const wctx = work.getContext('2d')
  if (!wctx) throw new Error('no 2d context')
  const r = fitRects(image, over, 'cover')
  wctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, r.dx, r.dy, r.dw, r.dh)

  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no 2d context')
  ctx.imageSmoothingEnabled = true

  if (canvasFilterSupported(ctx)) {
    ctx.filter = `blur(${radius}px)`
    ctx.drawImage(work, -radius, -radius)
    ctx.filter = 'none'
  } else {
    // Pyramid: down to a quarter, back to half, then to full — three smoothing passes.
    const quarter = document.createElement('canvas')
    quarter.width = Math.max(1, Math.round(over.width / 4))
    quarter.height = Math.max(1, Math.round(over.height / 4))
    quarter.getContext('2d')!.drawImage(work, 0, 0, quarter.width, quarter.height)
    const half = document.createElement('canvas')
    half.width = Math.max(1, Math.round(over.width / 2))
    half.height = Math.max(1, Math.round(over.height / 2))
    half.getContext('2d')!.drawImage(quarter, 0, 0, half.width, half.height)
    ctx.drawImage(half, -radius, -radius, over.width, over.height)
  }

  ctx.fillStyle = `rgba(0, 0, 0, ${BLUR_DIM})`
  ctx.fillRect(0, 0, w, h)
}
