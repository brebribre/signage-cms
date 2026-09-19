import { KIND_TEXT, KIND_WEB, type ManifestElement, type ManifestSlot, type TextStyle } from '../api'
import { STREAM_SOURCE_PREFIX } from '../engine'
import { blurSource, posterKey } from '../sceneBackground'
import { feedStream, type StreamFeed } from './streamFeed'
import { canvasSupported, paintBlur, paintPicture, type Box, type Fit } from './pictures'

/**
 * The loop — the Android player's `playback/PlaybackSurface.kt`, in the DOM.
 *
 * **Advance policy**, identical to Android's:
 * - A playlist of exactly one slot has nothing to advance to. What is on screen stays; a video in
 *   it repeats; its duration only decides how often the play is reported.
 * - A slot that is exactly one video advances when the video ends — or when the watchdog decides
 *   it never will ([DEFAULT_VIDEO_CAP_SECONDS]).
 * - Anything else (a picture, a website, any multi-element slot) advances on a plain timer set to
 *   the slot's own duration, and every video inside it loops.
 *
 * Elements are laid out from the same normalized x/y/width/height the CMS's scene editor uses,
 * painted in manifest order (later on top), with `fit` meaning exactly what CSS `object-fit`
 * already means — the editor's preview *is* object-fit, so the two cannot drift.
 */

/** A decoder that never reports its end must not wedge the screen for a shift. */
const DEFAULT_VIDEO_CAP_SECONDS = 90
const STALL_GRACE_MILLIS = 5_000
const CROSSFADE_MILLIS = 300
/** How long a new slot may take to get its first frame decoded before it is shown anyway. */
const FIRST_FRAME_TIMEOUT_MILLIS = 4_000
/** A playing video whose position hasn't moved in this many checks is stuck, not slow. */
const STALL_CHECK_MILLIS = 5_000
const STALL_CHECKS = 3
/** Restarts of one stuck video before its slot gives up on it (when the slot can advance). */
const MAX_STALL_RESTARTS = 2
/** A video with no picture after this long is reported, with what state it is stuck in. */
const NO_PICTURE_MILLIS = 6_000

export interface PlaybackCallbacks {
  onPlayed: (slot: ManifestSlot, startedAtMillis: number, seconds: number) => void
  onError: (message: string) => void
  /** 0-1, read whenever a video with sound starts or the CMS changes it. */
  volume: () => number
}

const objectFit = (fit: string | undefined) => (fit === 'cover' ? 'cover' : fit === 'stretch' ? 'fill' : 'contain')

export class PlaybackSurface {
  private slots: ManifestSlot[] = []
  private sources: Record<string, string> = {}
  /** The last video's state as it left the screen — so the debug overlay, opened during a
   *  picture, can still say what happened to the video before it. */
  private lastVideo: string | null = null
  private key = ''
  private index = 0
  private startedAt = Date.now()
  private layer: HTMLElement | null = null
  private timers: number[] = []
  private soundBlockedReported = false
  private autoplayBlockedReported = false
  /** Pictures a layer is still painting — what [firstFrame] waits for besides `<img>` loads. */
  private painting = new WeakMap<HTMLElement, Array<Promise<void>>>()
  /** The next slot's pictures and blurred background, rendered while the current slot plays,
   *  so the swap is a move of finished canvases rather than a decode. Keyed by slot index and
   *  stage size; anything else is thrown away unused. See ui/pictures.ts. */
  private prepared: {
    index: number
    stage: string
    pictures: Map<number, HTMLCanvasElement>
    background: HTMLCanvasElement | null
  } | null = null
  private readonly canvases = canvasSupported()
  /** Per-layer cleanups (a video's stall watchdog), run when that layer is torn down. */
  private cleanups = new WeakMap<HTMLElement, Array<() => void>>()
  /** Dropped-frame bookkeeping for [takeDroppedFrames]: what each video had last reported, and
   *  the deltas of videos already gone. */
  private droppedSeen = new WeakMap<HTMLVideoElement, number>()
  private droppedCarried = 0

  constructor(private readonly root: HTMLElement, private readonly cb: PlaybackCallbacks) {}

  /** A playlist identical to the one already looping (a restore followed by the same manifest
   *  from the network) keeps its place instead of starting over. */
  setPlaylist(slots: ManifestSlot[], sources: Record<string, string>) {
    // Only a change to *what* plays restarts the loop. New addresses for the same files (every
    // full manifest re-issues them) apply from the next slot on, without cutting off what's on
    // screen now.
    this.sources = sources
    // Addresses left out: they are presigned and re-issued on every full manifest, while the
    // checksum beside each one already names the content (a website's included).
    const key = JSON.stringify(slots, (k, v) => (k === 'url' ? undefined : v))
    if (key === this.key) return
    this.key = key
    this.slots = slots
    this.index = 0
    this.startedAt = Date.now()
    this.prepared = null
    this.show()
  }

  /** Re-lays out the current slot after the stage changes size (a rotation, a resize). */
  relayout() {
    this.prepared = null
    if (this.slots.length) this.show(false)
  }

  applyVolume() {
    this.layer?.querySelectorAll('video').forEach((v) => {
      if (!v.muted) v.volume = this.cb.volume()
    })
  }

  destroy() {
    this.clearTimers()
    this.root.querySelectorAll('.slot').forEach((el) => this.teardown(el as HTMLElement))
    this.layer = null
    this.key = ''
    this.prepared = null
  }

  private stageKey(width: number, height: number) {
    return `${width}x${height}`
  }

  /** The box, in stage pixels, an element's picture is drawn into — the pre-rotation box, since
   *  rotation is applied to the wrapper around it. */
  private innerBox(element: ManifestElement, width: number, height: number): Box {
    const boxW = width * (element.width ?? 1)
    const boxH = height * (element.height ?? 1)
    const rotation = element.rotation_degrees ?? 0
    const swapped = rotation === 90 || rotation === 270
    return { width: swapped ? boxH : boxW, height: swapped ? boxW : boxH }
  }

  /** A canvas for one picture, painted now unless [prepared] already has it. Never rejects: a
   *  picture that will not draw is reported and leaves its box transparent, as a broken `<img>`
   *  would, and the slot still advances on time. */
  private pictureCanvas(layer: HTMLElement, element: ManifestElement, position: number, url: string, box: Box, fit: Fit): HTMLCanvasElement {
    const ready = this.prepared?.index === this.index ? this.prepared.pictures.get(position) : undefined
    if (ready) {
      this.prepared!.pictures.delete(position)
      return ready
    }
    const canvas = document.createElement('canvas')
    this.track(layer, paintPicture(canvas, url, box, fit).catch(() => {
      this.cb.onError(`${this.nameOf(element)}: image failed to load`)
    }))
    return canvas
  }

  private track(layer: HTMLElement, work: Promise<void>) {
    const list = this.painting.get(layer) ?? []
    list.push(work)
    this.painting.set(layer, list)
  }

  /**
   * Renders the next slot's pictures and background while this one plays, so that when it is
   * due the canvases are moved into place, already painted. The decode is what a TV cannot hide
   * mid-transition; done here it lands while nothing is changing on screen. Videos and websites
   * are left alone — a video's decoder must not be held by a slot that is not on screen.
   */
  private prepareNext(width: number, height: number) {
    this.prepared = null
    if (!this.canvases || this.slots.length < 2) return
    const index = (this.index + 1) % this.slots.length
    const slot = this.slots[index]
    const prepared = { index, stage: this.stageKey(width, height), pictures: new Map<number, HTMLCanvasElement>(), background: null as HTMLCanvasElement | null }
    slot.elements.forEach((element, position) => {
      if (element.kind !== 'image') return
      const canvas = document.createElement('canvas')
      const url = this.sources[element.checksum] ?? element.url
      prepared.pictures.set(position, canvas)
      // A failure here is not reported: the slot will try again when it is shown, and report then.
      void paintPicture(canvas, url, this.innerBox(element, width, height), objectFit(element.fit)).catch(() => {
        if (this.prepared === prepared) prepared.pictures.delete(position)
      })
    })
    const blur = this.blurUrl(slot)
    if (blur) {
      const canvas = document.createElement('canvas')
      canvas.className = 'blur-bg'
      prepared.background = canvas
      void paintBlur(canvas, blur, { width, height }).catch(() => {
        if (this.prepared === prepared) prepared.background = null
      })
    }
    this.prepared = prepared
  }

  private get slot(): ManifestSlot {
    return this.slots[Math.min(this.index, this.slots.length - 1)]
  }

  private clearTimers() {
    this.timers.forEach((t) => clearTimeout(t))
    this.timers = []
  }

  private later(ms: number, fn: () => void) {
    this.timers.push(window.setTimeout(fn, ms))
  }

  private advance() {
    const now = Date.now()
    this.cb.onPlayed(this.slot, this.startedAt, Math.round((now - this.startedAt) / 1000))
    this.startedAt = now
    this.index = (this.index + 1) % this.slots.length
    this.show()
  }

  /** The one-slot counterpart of [advance]: record the play, change nothing on screen. */
  private report() {
    const now = Date.now()
    this.cb.onPlayed(this.slot, this.startedAt, Math.round((now - this.startedAt) / 1000))
    this.startedAt = now
  }

  private show(fade = true) {
    this.clearTimers()
    const slot = this.slot
    const onlySlot = this.slots.length === 1
    const singleVideo = slot.elements.length === 1 && slot.elements[0].kind === 'video'
    const loop = !singleVideo || onlySlot
    const durationMs = Math.max(1, slot.duration_seconds) * 1000

    let finished = false
    const finishOnce = (reason: string | null) => {
      if (finished) return
      finished = true
      if (reason) this.cb.onError(reason)
      this.advance()
    }

    const previous = this.layer
    // Free the outgoing slot's video decoders *before* the new slot asks for one. Most TVs have
    // exactly one hardware video decoder (some two); a new video that can't get one never paints a
    // frame and usually reports no error either — a black screen that just sits there. This is the
    // browser's version of the bug the Android player's surface pool exists to avoid.
    const previousHadVideo = !!previous?.querySelector('video')
    if (previous) this.releaseVideos(previous)

    const layer = document.createElement('div')
    layer.className = 'slot'
    const width = this.root.clientWidth
    const height = this.root.clientHeight
    // Prepared for a different size (a rotation landed in between) is prepared for nothing.
    if (this.prepared && this.prepared.stage !== this.stageKey(width, height)) this.prepared = null

    // A blurred scene's background goes in first, so every element paints over it.
    const background = this.blurredBackground(layer, slot, width, height)
    if (background) layer.appendChild(background)

    slot.elements.forEach((element, z) => {
      const box = document.createElement('div')
      box.className = 'el'
      const x = element.x ?? 0
      const y = element.y ?? 0
      const w = element.width ?? 1
      const h = element.height ?? 1
      Object.assign(box.style, {
        left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%`, zIndex: String(z),
      })

      // Rotation, as Android's RotatedContent: measured at the pre-rotation aspect and turned
      // to fill the box exactly.
      const rotation = element.rotation_degrees ?? 0
      const inner = document.createElement('div')
      inner.className = 'el-inner'
      const boxW = width * w
      const boxH = height * h
      const swapped = rotation === 90 || rotation === 270
      const innerW = swapped ? boxH : boxW
      const innerH = swapped ? boxW : boxH
      Object.assign(inner.style, {
        width: `${innerW}px`, height: `${innerH}px`,
        left: `${(boxW - innerW) / 2}px`, top: `${(boxH - innerH) / 2}px`,
        transform: rotation ? `rotate(${rotation}deg)` : '',
      })

      inner.appendChild(this.render(layer, element, z, { width: innerW, height: innerH }, loop, singleVideo && !onlySlot ? finishOnce : null))
      box.appendChild(inner)
      layer.appendChild(box)
    })
    // Whatever was prepared has now been used or was for another slot; start on the next one.
    this.prepareNext(width, height)

    // The new slot goes in *underneath* the old one, fully opaque, and the old one stays on top
    // until the new one has something to show — so a picture never gives way to a black box while
    // a video is still opening. Only pictures and websites fade: many TVs draw video on a separate
    // hardware plane beneath the page, and an opacity transition over one tends to show black.
    if (previous) this.root.insertBefore(layer, previous)
    else this.root.appendChild(layer)
    this.layer = layer
    if (previous && previousHadVideo) {
      // Its videos were just released, so it has nothing left worth keeping on top.
      this.teardown(previous)
    } else if (previous) {
      const hasVideo = slot.elements.some((el) => el.kind === 'video')
      void this.firstFrame(layer).then(() => {
        if (fade && !hasVideo) {
          // On the next frame, so the new layer underneath has been painted before the old one
          // starts to go — otherwise the first frames of the fade show the old slot over black.
          requestAnimationFrame(() => {
            previous.style.transition = `opacity ${CROSSFADE_MILLIS}ms linear`
            previous.style.opacity = '0'
            window.setTimeout(() => this.teardown(previous), CROSSFADE_MILLIS)
          })
        } else {
          this.teardown(previous)
        }
      })
    }

    if (onlySlot) {
      const tick = () => {
        this.report()
        this.later(durationMs, tick)
      }
      this.later(durationMs, tick)
    } else if (!singleVideo) {
      this.later(durationMs, () => this.advance())
    } else {
      // Watchdog: only the single-video path has a "should have finished by now".
      this.later(DEFAULT_VIDEO_CAP_SECONDS * 1000 + STALL_GRACE_MILLIS, () => {
        console.warn('[FortuPlayer]', `video did not finish within ${DEFAULT_VIDEO_CAP_SECONDS}s — advancing`)
        finishOnce(`${this.nameOf(slot.elements[0])}: did not finish in time`)
      })
    }
  }

  /**
   * The picture behind a blurred scene (see sceneBackground.ts): the source image itself, or a
   * video's thumbnail — never the video again, which would need a second hardware decoder most
   * TVs don't have. Blurred in proportion to the screen, dimmed so the scene stands out, and
   * scaled up a little so the blur's soft edges fall outside the screen.
   */
  private blurUrl(slot: ManifestSlot): string | null {
    const source = blurSource(slot)
    if (!source) return null
    const url = source.kind === 'image'
      ? this.sources[source.checksum] ?? source.url
      : this.sources[posterKey(source)] ?? source.poster_url
    return url ?? null
  }

  private blurredBackground(layer: HTMLElement, slot: ManifestSlot, width: number, height: number): HTMLElement | null {
    const url = this.blurUrl(slot)
    if (!url) return null
    if (this.canvases) {
      const ready = this.prepared?.index === this.index ? this.prepared.background : null
      if (ready) {
        this.prepared!.background = null
        return ready
      }
      const canvas = document.createElement('canvas')
      canvas.className = 'blur-bg'
      // A missing thumbnail leaves plain black, as before; nothing to report.
      this.track(layer, paintBlur(canvas, url, { width, height }).catch(() => { canvas.remove() }))
      return canvas
    }
    // No canvas: the browser's own blur, which is what this player did before ui/pictures.ts.
    const img = document.createElement('img')
    img.className = 'blur-bg blur-bg-filtered'
    img.decoding = 'async'
    img.style.filter = `blur(${Math.round(width * 0.03)}px) brightness(0.75)`
    img.onerror = () => img.remove()
    img.src = url
    return img
  }

  private nameOf(element: ManifestElement) {
    return element.media_id ?? element.id
  }

  /** Resolves once every picture and video in [layer] has something to show, or after
   *  [FIRST_FRAME_TIMEOUT_MILLIS] — a file that never loads must not hold the old slot forever. */
  private firstFrame(layer: HTMLElement): Promise<void> {
    const waits: Array<Promise<void>> = [...(this.painting.get(layer) ?? [])]
    layer.querySelectorAll('img').forEach((img) => {
      if (!img.complete) waits.push(new Promise((r) => { img.addEventListener('load', () => r(), { once: true }); img.addEventListener('error', () => r(), { once: true }) }))
    })
    layer.querySelectorAll('video').forEach((video) => {
      if (video.readyState < 2) waits.push(new Promise((r) => { video.addEventListener('loadeddata', () => r(), { once: true }); video.addEventListener('error', () => r(), { once: true }) }))
    })
    const timeout = new Promise<void>((r) => window.setTimeout(r, FIRST_FRAME_TIMEOUT_MILLIS))
    return Promise.race([Promise.all(waits).then(() => undefined), timeout])
  }

  /**
   * Frames the browser's decoder dropped since the last call, across every video that played
   * in between — the browser's `getVideoPlaybackQuality()`, which counts per element, turned
   * into one delta per heartbeat. Zero where the browser doesn't offer the count.
   */
  takeDroppedFrames(): number {
    let total = this.droppedCarried
    this.droppedCarried = 0
    this.layer?.querySelectorAll('video').forEach((v) => { total += this.droppedDelta(v) })
    return total
  }

  private droppedDelta(video: HTMLVideoElement): number {
    const now = video.getVideoPlaybackQuality?.()?.droppedVideoFrames ?? 0
    const delta = Math.max(0, now - (this.droppedSeen.get(video) ?? 0))
    this.droppedSeen.set(video, now)
    return delta
  }

  /** What the first video on screen is doing, for the debug overlay — the one place a black
   *  screen can be told apart: still loading, stuck, refused by the decoder, or blocked. */
  videoStatus(): string {
    const video = this.layer?.querySelector('video')
    if (!video) return this.lastVideo ? `last one: ${this.lastVideo}` : 'none played yet'
    return this.describe(video)
  }

  private describe(video: HTMLVideoElement): string {
    if (video.error) return `error ${video.error.code}: ${video.error.message || 'cannot decode this file'}`
    const states = ['no data', 'metadata only', 'first frame', 'buffering ahead', 'playing through']
    const size = video.videoWidth ? ` · ${video.videoWidth}×${video.videoHeight}` : ''
    const where = `${video.currentTime.toFixed(1)}s${Number.isFinite(video.duration) ? ` of ${video.duration.toFixed(0)}s` : ''}`
    const from = video.dataset.source ? ` · ${video.dataset.source}` : ''
    return `${video.paused ? 'paused' : 'playing'} ${where} · ${states[video.readyState] ?? video.readyState}${size}${from}${video.muted ? ' · muted' : ''}`
  }

  private render(layer: HTMLElement, element: ManifestElement, position: number, box: Box, loop: boolean, onFinished: ((reason: string | null) => void) | null): HTMLElement {
    const src = this.sources[element.checksum] ?? element.url
    const fit = objectFit(element.fit)

    if (element.kind === 'image' && this.canvases) {
      return this.pictureCanvas(layer, element, position, src, box, fit)
    }

    if (element.kind === 'image') {
      const img = document.createElement('img')
      img.decoding = 'async'
      img.style.objectFit = fit
      img.onerror = () => this.cb.onError(`${this.nameOf(element)}: image failed to load`)
      img.src = src
      return img
    }

    if (element.kind === 'video') {
      const video = document.createElement('video')
      video.playsInline = true
      video.autoplay = true
      video.preload = 'auto'
      video.style.objectFit = fit
      video.setAttribute('playsinline', '')
      // Every video is silent unless the CMS says it carries sound, same as Android.
      video.muted = !element.has_audio
      if (element.has_audio) video.volume = this.cb.volume()
      // A stored copy is fed through MediaSource (see ui/streamFeed.ts); anything else plays from
      // its address. If the browser refuses the stored copy, the video falls back to its address
      // for the rest of this slot — and says why, so the CMS shows it.
      const stored = src.startsWith(STREAM_SOURCE_PREFIX) && !!element.stream_mime
      let useStored = stored
      let feed: StreamFeed | null = null
      const start = () => {
        feed?.destroy()
        feed = null
        if (useStored) {
          video.dataset.source = 'saved copy'
          feed = feedStream(
            video,
            src.slice(STREAM_SOURCE_PREFIX.length),
            element.stream_mime!,
            (reason) => { fallBack(reason) },
            { loop },
          )
        } else {
          video.dataset.source = 'network'
          video.src = element.url
        }
        this.play(video)
      }
      const fallBack = (reason: string): boolean => {
        if (!useStored) return false
        useStored = false
        this.cb.onError(`${this.nameOf(element)}: saved copy wouldn't play (${reason}) — playing from the network`)
        start()
        return true
      }

      // Loops in place, stored copy or not: the browser jumps back to the start of what's already
      // buffered, with no new source and so no blank frame between loops. (Rebuilding the feed at
      // every loop is what used to flash a one-video playlist.) If a long video's start was dropped
      // to save memory, the feed puts it back as the jump happens — see feedStream's `loop`.
      video.loop = loop
      video.onended = () => {
        if (onFinished) onFinished(null)
        else if (loop) {
          // Some TV browsers ignore `loop` for certain files and stop on the last frame instead:
          // do the same jump by hand.
          video.currentTime = 0
          this.play(video)
        }
      }
      video.onerror = () => {
        const message = `${this.nameOf(element)}: ${video.error?.message || `media error ${video.error?.code ?? ''}`}`
        if (fallBack(`error ${video.error?.code ?? ''}`)) return
        // One unplayable file must never stop the loop on a black screen.
        if (onFinished) onFinished(message)
        else this.cb.onError(message)
      }
      start()
      this.later(NO_PICTURE_MILLIS, () => {
        if (video.isConnected && video.readyState < 2 && !video.error) {
          const why = `no picture after ${NO_PICTURE_MILLIS / 1000}s (${this.describe(video)})`
          if (!fallBack(why)) this.cb.onError(`${this.nameOf(element)}: ${why}`)
        }
      })
      this.onCleanup(layer, () => feed?.destroy())
      this.watchForStall(layer, video, element, onFinished, (at) => {
        if (useStored) return start()
        video.addEventListener('loadedmetadata', () => { if (at > 0) video.currentTime = at }, { once: true })
        video.load()
        this.play(video)
      })
      return video
    }

    if (element.kind === KIND_TEXT) return this.renderText(element)

    if (element.kind === KIND_WEB) {
      // Live, and usable by touch, like Android's WebView. A site that forbids being framed
      // (X-Frame-Options / frame-ancestors) shows the browser's own refusal page here — that is
      // the site's decision, and nothing a page can detect or work around.
      const frame = document.createElement('iframe')
      frame.setAttribute('allow', 'autoplay; fullscreen; encrypted-media')
      frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin')
      frame.src = src
      return frame
    }

    // A kind this build predates — nothing to render, but not a crash.
    return document.createElement('div')
  }

  /**
   * Text, drawn the way the CMS preview draws it (frontend utils/textStyle.ts): the box carries
   * the background, the words sit vertically centred, wrap inside the box, and are aligned as
   * asked. The size is a fraction of the stage's height — the screen's own — not the box's.
   */
  private renderText(element: ManifestElement): HTMLElement {
    const style: TextStyle = {
      size: 0.06, color: '#FFFFFF', weight: 'bold', align: 'center', background: null,
      ...(element.text_style ?? {}),
    }
    const px = Math.max(1, style.size * this.root.clientHeight)
    const box = document.createElement('div')
    box.className = 'text'
    Object.assign(box.style, {
      justifyContent: style.align === 'left' ? 'flex-start' : style.align === 'right' ? 'flex-end' : 'center',
      padding: `${px * 0.25}px`,
      background: style.background ?? 'transparent',
      color: style.color,
      fontSize: `${px}px`,
      fontWeight: style.weight === 'bold' ? '700' : '400',
      textAlign: style.align,
    })
    box.textContent = element.text ?? ''
    return box
  }

  /** Browsers refuse to start a video with sound until someone has interacted with the page.
   *  A screen nobody touches would otherwise sit on a frozen frame, so it plays muted instead —
   *  and says why, once, so the fix (the TV browser's autoplay setting) is findable. */
  private play(video: HTMLVideoElement) {
    const attempt = video.play()
    if (!attempt) return
    attempt.catch((e: DOMException) => {
      if (e?.name !== 'NotAllowedError') return
      if (video.muted) {
        // Refused even silent — this browser allows no autoplay at all, so the video sits on
        // black until someone presses a key. Only the TV browser's own settings can change that.
        if (!this.autoplayBlockedReported) {
          this.autoplayBlockedReported = true
          this.cb.onError("The browser won't start video on its own — allow autoplay in the TV browser's settings, or press a key on the remote")
        }
        return
      }
      video.muted = true
      void video.play().catch(() => {})
      if (!this.soundBlockedReported) {
        this.soundBlockedReported = true
        this.cb.onError('The browser blocked sound until someone interacts with the screen — playing muted')
      }
    })
  }

  /**
   * A video that stops moving with no error — the decoder wedged, the network stalled while
   * streaming, the TV quietly paused it — is restarted rather than left black. On the single-video
   * path, a video that keeps sticking gives way to the next slot, like Android's watchdog.
   */
  private watchForStall(
    layer: HTMLElement,
    video: HTMLVideoElement,
    element: ManifestElement,
    onFinished: ((reason: string | null) => void) | null,
    restart: (at: number) => void,
  ) {
    let lastTime = -1
    let stuckChecks = 0
    let restarts = 0
    const timer = window.setInterval(() => {
      // A hidden page (the TV switched to another app or input) pauses video by design.
      if (video.ended || video.error || document.hidden) return
      const moving = video.currentTime !== lastTime && !video.paused
      lastTime = video.currentTime
      if (moving) {
        stuckChecks = 0
        return
      }
      if (video.paused) this.play(video) // quietly paused by the browser: just ask again
      if (++stuckChecks < STALL_CHECKS) return
      stuckChecks = 0
      restarts++
      if (onFinished && restarts > MAX_STALL_RESTARTS) {
        onFinished(`${this.nameOf(element)}: video kept stalling — skipped`)
        return
      }
      this.cb.onError(`${this.nameOf(element)}: video stuck at ${video.currentTime.toFixed(1)}s — restarting it`)
      restart(video.currentTime)
    }, STALL_CHECK_MILLIS)
    this.onCleanup(layer, () => clearInterval(timer))
  }

  private onCleanup(layer: HTMLElement, fn: () => void) {
    const list = this.cleanups.get(layer) ?? []
    list.push(fn)
    this.cleanups.set(layer, list)
  }

  /** Stops a layer's videos and gives their decoders back, leaving the layer itself in place. */
  private releaseVideos(layer: HTMLElement) {
    // Described before anything is stopped, so the overlay shows how it was actually playing —
    // and its dropped frames banked, so a video that ends between heartbeats still counts.
    layer.querySelectorAll('video').forEach((v) => {
      if (v.currentSrc) this.lastVideo = this.describe(v)
      this.droppedCarried += this.droppedDelta(v)
    })
    this.cleanups.get(layer)?.forEach((fn) => fn())
    this.cleanups.delete(layer)
    layer.querySelectorAll('video').forEach((v) => {
      v.onended = null
      v.onerror = null
      v.pause()
      v.removeAttribute('src')
      v.load()
    })
  }

  private teardown(layer: HTMLElement) {
    this.painting.delete(layer)
    this.releaseVideos(layer)
    layer.remove()
  }
}
