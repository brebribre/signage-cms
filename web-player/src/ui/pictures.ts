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

export interface Box {
  width: number
  height: number
}

export type Fit = 'contain' | 'cover' | 'fill'

/** The largest canvas side we ask for. A TV browser that is short of GPU memory fails to paint
 *  a bigger one silently, and nothing on a wall needs more than this. */
const MAX_CANVAS_SIDE = 4096
/** The blurred background's own size: small enough that scaling it to the screen is the blur. */
const BLUR_WIDTH = 96
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
 *  transparent until this lands, like an `<img>` before its first paint. */
export async function paintPicture(canvas: HTMLCanvasElement, url: string, box: Box, fit: Fit): Promise<void> {
  const img = await loadImage(url)
  const size = canvasSize(box)
  canvas.width = size.width
  canvas.height = size.height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no 2d context')
  const r = fitRects({ width: img.naturalWidth, height: img.naturalHeight }, size, fit)
  ctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, r.dx, r.dy, r.dw, r.dh)
}

/** Draws a blurred, dimmed, cover-fitted copy of `url` into `canvas`, at BLUR_WIDTH across. The
 *  canvas is then stretched to the stage by CSS, and that stretch is the blur. Two passes down
 *  (a single 40:1 draw would alias into blocks on some browsers) and one back up. */
export async function paintBlur(canvas: HTMLCanvasElement, url: string, stage: Box): Promise<void> {
  const img = await loadImage(url)
  const aspect = stage.width / Math.max(1, stage.height)
  const w = BLUR_WIDTH
  const h = Math.max(1, Math.round(w / aspect))

  // Pass 1: cover-fit to a quarter-size intermediate.
  const mid = document.createElement('canvas')
  mid.width = w * 4
  mid.height = h * 4
  const mctx = mid.getContext('2d')
  if (!mctx) throw new Error('no 2d context')
  const r = fitRects({ width: img.naturalWidth, height: img.naturalHeight }, { width: mid.width, height: mid.height }, 'cover')
  mctx.drawImage(img, r.sx, r.sy, r.sw, r.sh, r.dx, r.dy, r.dw, r.dh)

  // Pass 2: down to the final size, then dim.
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no 2d context')
  ctx.imageSmoothingEnabled = true
  ctx.drawImage(mid, 0, 0, w, h)
  ctx.fillStyle = `rgba(0, 0, 0, ${BLUR_DIM})`
  ctx.fillRect(0, 0, w, h)
}
