import '@fontsource-variable/inter'
import '@fontsource-variable/outfit'
import './style.css'

import { ApiClient, type ManifestSettings } from './api'
import { PlayerEngine, type PlayerState } from './engine'
import { CacheStorageMedia } from './mediaCache'
import { LocalDeviceStore } from './store'
import { renderDebug } from './ui/debug'
import { PlaybackSurface } from './ui/playback'
import { statusScreenHtml } from './ui/screens'

/**
 * The browser shell around [PlayerEngine] — the web counterpart of the Android player's
 * `MainActivity` + `PlayerViewModel` + `kiosk/DeviceSettingsApplier`. Everything that can be
 * wrong lives in the engine, which has its own tests; this only wires it to the page.
 */

declare const __PLAYER_VERSION__: string

const TAG = '[FortuPlayer]'
const API_HOST_KEY = 'fortu_player.api_host'
/** How often a running screen looks for a newer deploy of this player. */
const UPDATE_CHECK_MILLIS = 5 * 60 * 1000
const LONG_PRESS_MILLIS = 900
const LONG_PRESS_SLOP_PX = 24
const HIDDEN_CORNER_FRACTION = 0.2
const DEBUG_AUTO_DISMISS_MILLIS = 10_000

const app = document.getElementById('app')!
app.innerHTML = '<div id="stage"></div>'
const stage = document.getElementById('stage')!

interface VersionInfo {
  version: string
  build: string
  apiHost: string
}

async function fetchVersion(timeoutMs = 5_000): Promise<VersionInfo | null> {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const res = await fetch('/version.json', { cache: 'no-store', signal: controller.signal })
    clearTimeout(timer)
    return res.ok ? await res.json() : null
  } catch {
    return null
  }
}

function readLocal(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

async function boot() {
  // Which backend the proxy points at, for the pairing screen. Remembered, so a screen booting
  // with no network still names its server.
  const booted = await fetchVersion(3_000)
  if (booted) {
    try { localStorage.setItem(API_HOST_KEY, booted.apiHost) } catch { /* shown, just not remembered */ }
  }
  const apiHost = booted?.apiHost ?? readLocal(API_HOST_KEY) ?? location.host
  let currentBuild = booted?.build ?? null

  // --- Screen state the engine reads back -------------------------------------------------

  let settings: ManifestSettings = {}
  let powered = true
  let wakeLock: { release(): Promise<void> } | null = null
  let wakeLockState = 'wakeLock' in navigator ? 'not held' : 'unsupported by this browser'

  const volume = () => (settings.volume ?? 100) / 100

  const cache = new CacheStorageMedia()
  // Asked once: without it the browser may clear the media cache under storage pressure.
  navigator.storage?.persist?.().catch(() => {})

  const engine = new PlayerEngine({
    api: new ApiClient('/api'),
    store: new LocalDeviceStore(),
    cache,
    appVersion: __PLAYER_VERSION__,
    apiHost,
    applySettings: (next) => {
      settings = next
      surface.applyVolume()
      applyTouchLock()
    },
    currentSettings: () => ({ volume: Math.round(volume() * 100), power_state: powered ? 'on' : 'off' }),
    droppedFrames: () => surface.takeDroppedFrames(),
    applyPower: (on) => {
      powered = on
      render()
      void syncWakeLock()
    },
    warmMedia: async (url, kind) => {
      if (kind !== 'image') return
      const img = new Image()
      img.src = url
      await img.decode()
    },
    // Videos are stored for offline play only where MediaSource can play their streaming copy —
    // see storedFile in engine.ts. Checked per codec string, so an unsupported one streams.
    canPlayStream: (mime) => {
      try { return !!window.MediaSource && MediaSource.isTypeSupported(mime) } catch { return false }
    },
    screenSize: () => ({
      width: Math.round(window.innerWidth * (window.devicePixelRatio || 1)),
      height: Math.round(window.innerHeight * (window.devicePixelRatio || 1)),
    }),
  })

  // --- Orientation --------------------------------------------------------------------------

  /** Set per screen in the CMS. A browser cannot turn the panel itself, so when the configured
   *  orientation disagrees with the panel's shape the whole stage is drawn turned a quarter,
   *  as a TV mounted on its side needs. Before the first manifest the panel is left as it is —
   *  a pairing code reads fine either way. */
  let rotated = false
  function applyOrientation() {
    const vw = window.innerWidth
    const vh = window.innerHeight
    const wanted = engine.orientation.value
    rotated = !!wanted && (wanted === 'portrait') !== vh > vw
    Object.assign(stage.style, rotated
      ? { width: `${vh}px`, height: `${vw}px`, transform: `translateX(${vw}px) rotate(90deg)` }
      : { width: '100%', height: '100%', transform: '' })
    surface.relayout()
  }

  /** A viewport point in the stage's own coordinates — the inverse of the rotation above. */
  function toStage(x: number, y: number) {
    return rotated ? { x: y, y: window.innerWidth - x } : { x, y }
  }

  // --- Rendering ----------------------------------------------------------------------------

  const surface = new PlaybackSurface(stage, {
    onPlayed: (slot, startedAt, seconds) => engine.reportPlay(slot, startedAt, seconds),
    onError: (message) => engine.reportError(message),
    volume,
  })

  const status = document.createElement('div')
  const sleep = document.createElement('div')
  sleep.id = 'sleep'
  const shield = document.createElement('div')
  shield.id = 'shield'
  const debugEl = document.createElement('div')
  debugEl.id = 'debug'
  const fullscreenHint = document.createElement('div')
  fullscreenHint.id = 'fs-hint'
  fullscreenHint.textContent = 'Press OK on the remote to hide the browser bar'

  let lastStatusHtml = ''
  function render() {
    const state: PlayerState = engine.state.value
    // Asleep means nothing playing at all, not content hidden behind black: a sleeping screen
    // should not be decoding video all night.
    if (!powered) {
      surface.destroy()
      status.remove()
      lastStatusHtml = ''
      if (!sleep.isConnected) stage.appendChild(sleep)
      syncFullscreenHint()
      return
    }
    sleep.remove()
    syncFullscreenHint()
    if (state.kind === 'playing') {
      status.remove()
      lastStatusHtml = ''
      surface.setPlaylist(state.slots, state.sources)
    } else {
      surface.destroy()
      const html = statusScreenHtml(state)
      if (html !== lastStatusHtml) {
        status.innerHTML = html
        lastStatusHtml = html
      }
      if (!status.isConnected) stage.appendChild(status)
    }
  }

  // --- Power: keep the panel awake while on, let it sleep while off --------------------------

  async function syncWakeLock() {
    const nav = navigator as Navigator & { wakeLock?: { request(type: 'screen'): Promise<{ release(): Promise<void> }> } }
    if (!nav.wakeLock) return
    if (powered && document.visibilityState === 'visible') {
      if (wakeLock) return
      try {
        wakeLock = await nav.wakeLock.request('screen')
        wakeLockState = 'held — the screen will not sleep'
        ;(wakeLock as unknown as EventTarget).addEventListener?.('release', () => {
          wakeLock = null
          wakeLockState = 'released'
        })
      } catch (e) {
        wakeLockState = `refused: ${(e as Error).message}`
      }
    } else if (wakeLock) {
      await wakeLock.release().catch(() => {})
      wakeLock = null
      wakeLockState = powered ? 'released (page hidden)' : 'released (power off)'
    }
  }
  document.addEventListener('visibilitychange', () => void syncWakeLock())

  // --- Touch lock and the hidden debug gesture ------------------------------------------------

  function applyTouchLock() {
    const locked = settings.touchscreen_disabled === true
    if (locked && !shield.isConnected) app.appendChild(shield)
    if (!locked) shield.remove()
    // A lock landing while someone has the overlay open closes it, as on Android.
    if (locked) setDebug(false)
  }

  let pressTimer: number | null = null
  let downX = 0
  let downY = 0
  const cancelPress = () => {
    if (pressTimer !== null) clearTimeout(pressTimer)
    pressTimer = null
  }

  const swallow = (e: Event) => {
    if (settings.touchscreen_disabled === true) {
      e.preventDefault()
      e.stopImmediatePropagation()
      return true
    }
    return false
  }
  for (const type of ['click', 'dblclick', 'contextmenu', 'wheel', 'touchstart', 'touchmove', 'mousedown']) {
    window.addEventListener(type, swallow, { capture: true, passive: false })
  }

  window.addEventListener('pointerdown', (e) => {
    if (swallow(e)) return
    downX = e.clientX
    downY = e.clientY
    const p = toStage(e.clientX, e.clientY)
    if (p.x <= stage.offsetWidth * HIDDEN_CORNER_FRACTION && p.y <= stage.offsetHeight * HIDDEN_CORNER_FRACTION) {
      cancelPress()
      pressTimer = window.setTimeout(() => {
        pressTimer = null
        setDebug(!debugEl.isConnected)
      }, LONG_PRESS_MILLIS)
    }
    requestFullscreen()
  }, true)
  window.addEventListener('pointermove', (e) => {
    if (Math.hypot(e.clientX - downX, e.clientY - downY) > LONG_PRESS_SLOP_PX) cancelPress()
  }, true)
  window.addEventListener('pointerup', cancelPress, true)
  window.addEventListener('pointercancel', cancelPress, true)

  window.addEventListener('keydown', (e) => {
    // Menu on a keyboard, Info on Samsung/LG remotes, or D. Keys still work under the touch
    // lock — the local way in when touch is off, same as Android's Menu key.
    const isDebugKey = e.key === 'ContextMenu' || e.key === 'Info' || e.keyCode === 457 || e.key === 'd' || e.key === 'D'
    if (isDebugKey) {
      e.preventDefault()
      setDebug(!debugEl.isConnected)
      requestFullscreen()
    } else if (e.key === 'Escape' && debugEl.isConnected) {
      setDebug(false)
    } else if (settings.touchscreen_disabled !== true) {
      requestFullscreen()
    }
  }, true)

  // --- Full screen ----------------------------------------------------------------------------

  /** A page may only go full screen in answer to someone's input — no browser lets it happen on
   *  load. So: try anyway at start (a few TV and kiosk browsers allow it), then take the first
   *  key press or touch, and say on the non-playing screens that one press is all it needs.
   *  Kiosk-mode browsers have no bar to hide and never need any of this. */
  // Full screen belongs to the page around this frame (src/shell.ts) — same origin, so it is
  // reachable directly. Opened on its own, this page is its own top.
  const topDocument = (() => {
    try { return window.top!.document } catch { return document }
  })()
  const doc = topDocument as Document & { webkitFullscreenElement?: Element; webkitFullscreenEnabled?: boolean }
  const root = topDocument.documentElement as HTMLElement & { webkitRequestFullscreen?: () => void }
  const fullscreenSupported = !!(doc.fullscreenEnabled || doc.webkitFullscreenEnabled)
  const isFullscreen = () => !!(doc.fullscreenElement || doc.webkitFullscreenElement)
  /** Set once the browser has refused a request made in answer to a real press — asking again
   *  would change nothing, and a hint promising otherwise would sit on the screen forever. */
  let fullscreenRefused = false

  function requestFullscreen(fromInput = true) {
    if (!fullscreenSupported || isFullscreen()) return
    try {
      if (root.requestFullscreen) {
        root.requestFullscreen().catch(() => {
          if (fromInput) {
            fullscreenRefused = true
            syncFullscreenHint()
          }
        })
      } else {
        root.webkitRequestFullscreen?.()
      }
    } catch {
      if (fromInput) fullscreenRefused = true
    }
  }

  /** Only over the pairing, preparing, idle and trouble screens — someone is usually standing at
   *  the TV for those, and it never sits on top of content. */
  function syncFullscreenHint() {
    const show = fullscreenSupported && !fullscreenRefused && !isFullscreen() && powered &&
      engine.state.value.kind !== 'playing'
    if (show && !fullscreenHint.isConnected) app.appendChild(fullscreenHint)
    if (!show) fullscreenHint.remove()
  }
  topDocument.addEventListener('fullscreenchange', syncFullscreenHint)
  topDocument.addEventListener('webkitfullscreenchange', syncFullscreenHint)

  // --- Debug overlay ------------------------------------------------------------------------

  let debugTimer: number | null = null
  function restartDebugTimer() {
    if (debugTimer !== null) clearTimeout(debugTimer)
    debugTimer = window.setTimeout(() => setDebug(false), DEBUG_AUTO_DISMISS_MILLIS)
  }
  function drawDebug() {
    if (!debugEl.isConnected) return
    renderDebug(
      debugEl,
      engine.debug.value,
      {
        player: `${__PLAYER_VERSION__} · ${navigator.userAgent.match(/(Tizen|Web0S|webOS|Android|CrOS|Windows|Mac OS X|Linux)/)?.[1] ?? 'browser'}`,
        screen: `${window.innerWidth}×${window.innerHeight} @${window.devicePixelRatio || 1}x${rotated ? ' · rotated' : ''}`,
        video: surface.videoStatus(),
        'wake lock': wakeLockState,
        'full screen': !fullscreenSupported ? 'not supported by this browser'
          : isFullscreen() ? 'yes' : fullscreenRefused ? 'refused by the browser' : 'no — press OK',
        power: powered ? 'on' : 'off',
      },
      { onCheckUpdate: () => void checkForUpdate(true), onReload: () => location.reload() },
    )
  }
  function setDebug(open: boolean) {
    if (open) {
      if (!debugEl.isConnected) app.appendChild(debugEl)
      drawDebug()
      restartDebugTimer()
    } else {
      debugEl.remove()
      if (debugTimer !== null) clearTimeout(debugTimer)
    }
  }
  debugEl.addEventListener('keydown', restartDebugTimer)
  setInterval(drawDebug, 1_000)

  // --- Updates: a new deploy of this player replaces the running one -------------------------

  /** The web counterpart of the Android player's self-update: nothing to install, just the newest
   *  deploy to load. Held off while content is still downloading, so a download isn't thrown
   *  away half done — the cache survives the reload either way.
   *
   *  Only this frame reloads, never the page around it (see src/shell.ts), so a screen that is
   *  full screen stays full screen across an update. */
  async function checkForUpdate(manual: boolean) {
    if (manual) {
      engine.setUpdateStatus('checking for update…')
      restartDebugTimer()
    }
    const latest = await fetchVersion()
    if (!latest) {
      if (manual) engine.setUpdateStatus('check failed: server unreachable')
      return
    }
    if (currentBuild === null) currentBuild = latest.build
    if (latest.build === currentBuild) {
      engine.setUpdateStatus(`up to date (${__PLAYER_VERSION__})`)
      return
    }
    if (engine.state.value.kind === 'preparing' && !manual) return
    engine.setUpdateStatus(`loading ${latest.version}…`)
    console.info(TAG, `new player deploy ${latest.build} — reloading`)
    location.reload()
  }
  setInterval(() => void checkForUpdate(false), UPDATE_CHECK_MILLIS)

  // --- Go ----------------------------------------------------------------------------------

  engine.state.subscribe(render)
  engine.orientation.subscribe(applyOrientation)
  engine.debug.subscribe(() => drawDebug())
  window.addEventListener('resize', applyOrientation)
  // The nearest thing to push a browser has: the network coming back ends the current wait.
  window.addEventListener('online', () => engine.nudge())

  // Opened directly rather than through the shell (src/shell.ts), which registers it otherwise.
  if (window.top === window && 'serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js').catch((e) => console.warn(TAG, 'service worker not registered', e))
  }

  void syncWakeLock()
  requestFullscreen(false)
  syncFullscreenHint()
  await engine.run()
}

void boot()
