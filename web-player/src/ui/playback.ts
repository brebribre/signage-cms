import { KIND_WEB, type ManifestElement, type ManifestSlot } from '../api'

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
  /** Per-layer cleanups (a video's stall watchdog), run when that layer is torn down. */
  private cleanups = new WeakMap<HTMLElement, Array<() => void>>()

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
    this.show()
  }

  /** Re-lays out the current slot after the stage changes size (a rotation, a resize). */
  relayout() {
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

      inner.appendChild(this.render(layer, element, loop, singleVideo && !onlySlot ? finishOnce : null))
      box.appendChild(inner)
      layer.appendChild(box)
    })

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
          previous.style.transition = `opacity ${CROSSFADE_MILLIS}ms linear`
          previous.style.opacity = '0'
          window.setTimeout(() => this.teardown(previous), CROSSFADE_MILLIS)
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

  private nameOf(element: ManifestElement) {
    return element.media_id ?? element.id
  }

  /** Resolves once every picture and video in [layer] has something to show, or after
   *  [FIRST_FRAME_TIMEOUT_MILLIS] — a file that never loads must not hold the old slot forever. */
  private firstFrame(layer: HTMLElement): Promise<void> {
    const waits: Array<Promise<void>> = []
    layer.querySelectorAll('img').forEach((img) => {
      if (!img.complete) waits.push(new Promise((r) => { img.addEventListener('load', () => r(), { once: true }); img.addEventListener('error', () => r(), { once: true }) }))
    })
    layer.querySelectorAll('video').forEach((video) => {
      if (video.readyState < 2) waits.push(new Promise((r) => { video.addEventListener('loadeddata', () => r(), { once: true }); video.addEventListener('error', () => r(), { once: true }) }))
    })
    const timeout = new Promise<void>((r) => window.setTimeout(r, FIRST_FRAME_TIMEOUT_MILLIS))
    return Promise.race([Promise.all(waits).then(() => undefined), timeout])
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
    return `${video.paused ? 'paused' : 'playing'} ${where} · ${states[video.readyState] ?? video.readyState}${size}${video.muted ? ' · muted' : ''}`
  }

  private render(layer: HTMLElement, element: ManifestElement, loop: boolean, onFinished: ((reason: string | null) => void) | null): HTMLElement {
    const src = this.sources[element.checksum] ?? element.url
    const fit = objectFit(element.fit)

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
      video.loop = loop
      video.style.objectFit = fit
      video.setAttribute('playsinline', '')
      // Every video is silent unless the CMS says it carries sound, same as Android.
      video.muted = !element.has_audio
      if (element.has_audio) video.volume = this.cb.volume()
      video.onended = () => {
        if (onFinished) onFinished(null)
        // Some TV browsers ignore `loop` for certain files and stop on the last frame instead.
        else if (loop) {
          video.currentTime = 0
          this.play(video)
        }
      }
      video.onerror = () => {
        const message = `${this.nameOf(element)}: ${video.error?.message || `media error ${video.error?.code ?? ''}`}`
        // One unplayable file must never stop the loop on a black screen.
        if (onFinished) onFinished(message)
        else this.cb.onError(message)
      }
      video.src = src
      this.play(video)
      this.later(NO_PICTURE_MILLIS, () => {
        if (video.isConnected && video.readyState < 2 && !video.error) {
          this.cb.onError(`${this.nameOf(element)}: no picture after ${NO_PICTURE_MILLIS / 1000}s (${this.describe(video)})`)
        }
      })
      this.watchForStall(layer, video, element, onFinished)
      return video
    }

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
  ) {
    let lastTime = -1
    let stuckChecks = 0
    let restarts = 0
    const timer = window.setInterval(() => {
      if (video.ended || video.error) return
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
      const at = video.currentTime
      video.addEventListener('loadedmetadata', () => { if (at > 0) video.currentTime = at }, { once: true })
      video.load()
      this.play(video)
    }, STALL_CHECK_MILLIS)
    const list = this.cleanups.get(layer) ?? []
    list.push(() => clearInterval(timer))
    this.cleanups.set(layer, list)
  }

  /** Stops a layer's videos and gives their decoders back, leaving the layer itself in place. */
  private releaseVideos(layer: HTMLElement) {
    this.cleanups.get(layer)?.forEach((fn) => fn())
    this.cleanups.delete(layer)
    layer.querySelectorAll('video').forEach((v) => {
      if (v.currentSrc) this.lastVideo = this.describe(v)
      v.onended = null
      v.onerror = null
      v.pause()
      v.removeAttribute('src')
      v.load()
    })
  }

  private teardown(layer: HTMLElement) {
    this.releaseVideos(layer)
    layer.remove()
  }
}
