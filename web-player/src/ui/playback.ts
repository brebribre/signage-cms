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
  private key = ''
  private index = 0
  private startedAt = Date.now()
  private layer: HTMLElement | null = null
  private timers: number[] = []
  private soundBlockedReported = false

  constructor(private readonly root: HTMLElement, private readonly cb: PlaybackCallbacks) {}

  /** A playlist identical to the one already looping (a restore followed by the same manifest
   *  from the network) keeps its place instead of starting over. */
  setPlaylist(slots: ManifestSlot[], sources: Record<string, string>) {
    const key = JSON.stringify([slots, sources])
    if (key === this.key) return
    this.key = key
    this.slots = slots
    this.sources = sources
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

      inner.appendChild(this.render(element, loop, singleVideo && !onlySlot ? finishOnce : null))
      box.appendChild(inner)
      layer.appendChild(box)
    })

    this.root.appendChild(layer)
    this.layer = layer
    if (fade && previous) {
      // Paint the new layer at 0, then fade it in over the old one, which keeps showing its
      // last frame underneath — never a black flash between two pictures.
      void layer.offsetWidth
      layer.classList.add('shown')
      window.setTimeout(() => this.teardown(previous), CROSSFADE_MILLIS)
    } else {
      layer.classList.add('shown')
      if (previous) this.teardown(previous)
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

  private render(element: ManifestElement, loop: boolean, onFinished: ((reason: string | null) => void) | null): HTMLElement {
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
      if (onFinished) video.onended = () => onFinished(null)
      video.onerror = () => {
        const message = `${this.nameOf(element)}: ${video.error?.message || `media error ${video.error?.code ?? ''}`}`
        // One unplayable file must never stop the loop on a black screen.
        if (onFinished) onFinished(message)
        else this.cb.onError(message)
      }
      video.src = src
      this.play(video)
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
      if (e?.name !== 'NotAllowedError' || video.muted) return
      video.muted = true
      void video.play().catch(() => {})
      if (!this.soundBlockedReported) {
        this.soundBlockedReported = true
        this.cb.onError('The browser blocked sound until someone interacts with the screen — playing muted')
      }
    })
  }

  private teardown(layer: HTMLElement) {
    layer.querySelectorAll('video').forEach((v) => {
      v.onended = null
      v.onerror = null
      v.pause()
      v.removeAttribute('src')
      v.load()
    })
    layer.remove()
  }
}
