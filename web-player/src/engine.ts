import {
  KIND_WEB,
  UnauthorizedError,
  type Manifest,
  type ManifestElement,
  type ManifestSettings,
  type ManifestSlot,
  type PlayerApi,
  type PlayReport,
} from './api'
import type { MediaStore } from './mediaCache'
import { decide, parseInstantMillis, resolveZone } from './powerPlan'
import type { TokenStore } from './store'

/**
 * The player's whole state machine, with no DOM — a port of the Android player's
 * `PlayerEngine.kt`, kept deliberately close to it so the two screens behave the same way and a
 * fix in one reads straight across to the other. Where this differs, it says why.
 *
 * The main difference is push: a browser cannot open the MQTT broker's raw TLS port, so there is
 * no early wake-up from the CMS. The poll interval is shorter instead (see [POLL_SECONDS]), and
 * a returning network connection wakes the loop at once (see [nudge]).
 */

const TAG = '[FortuPlayer]'

/** Everything the UI can be showing. The pairing screen doubles as the error state. */
export type PlayerState =
  | { kind: 'starting' }
  /** `apiHost` is shown on purpose: pairing "not working" is almost always the screen and the
   *  CMS pointed at different servers, and this is the only place that is visible. */
  | { kind: 'pairing'; code: string; apiHost: string; error: string | null; checks: number }
  | { kind: 'claimed'; deviceName: string }
  | { kind: 'preparing'; deviceName: string; done: number; total: number; currentFile: string | null }
  | { kind: 'idle'; deviceName: string }
  | { kind: 'trouble'; deviceName: string | null; message: string; apiHost: string; attempts: number }
  /** `sources` maps each element's checksum to the URL playback loads it from — the cached copy
   *  for a picture or a video with a streaming copy (see [storedFile]), otherwise the element's own
   *  address. */
  | { kind: 'playing'; slots: ManifestSlot[]; shuffle: boolean; sources: Record<string, string> }

export interface DebugInfo {
  deviceName: string | null
  version: string | null
  cachedBytes: number
  itemCount: number
  lastPollAt: number | null
  lastError: string | null
  /** When [lastError] happened. Errors stay shown until a newer one replaces them — clearing
   *  them on every successful poll wiped a playback error before anyone could read it. */
  lastErrorAt: number | null
  apiHost: string
  /** How content is stored: offline cache, or streaming because this browser can't keep files. */
  storage: string
  schedule: string | null
  /** Whether a newer deploy of the web player exists — the web counterpart of self-update. */
  updateStatus: string | null
}

type Listener<T> = (value: T) => void

/** The smallest observable that does the job: the latest value, and who wants to know. */
export class Signal<T> {
  private listeners = new Set<Listener<T>>()
  constructor(private current: T) {}
  get value(): T {
    return this.current
  }
  set(next: T) {
    this.current = next
    for (const l of this.listeners) l(next)
  }
  update(fn: (prev: T) => T) {
    this.set(fn(this.current))
  }
  subscribe(listener: Listener<T>): () => void {
    this.listeners.add(listener)
    listener(this.current)
    return () => this.listeners.delete(listener)
  }
}

export interface EngineOptions {
  api: PlayerApi
  store: TokenStore
  cache: MediaStore
  appVersion: string
  /** The backend's host, for the pairing and trouble screens. */
  apiHost: string
  /** Volume and the touch lock are applied by the UI shell — see main.ts. */
  applySettings?: (settings: ManifestSettings) => void
  /** What the screen's settings actually are right now, for the heartbeat to report. */
  currentSettings?: () => Record<string, string | number | boolean>
  /** Sleeps or wakes the screen. Called only when the power decision changes. */
  applyPower?: (on: boolean) => void
  /** Pre-decodes an image so its first showing isn't a cold decode. */
  warmMedia?: (url: string, kind: string) => Promise<void>
  screenSize?: () => { width: number; height: number } | null
  /** Whether this browser's MediaSource plays a streaming copy's MIME type — see [storedFile]. */
  canPlayStream?: (mime: string) => boolean
  clock?: () => number
}

export class PlayerEngine {
  readonly state = new Signal<PlayerState>({ kind: 'starting' })
  readonly debug: Signal<DebugInfo>
  readonly settings = new Signal<ManifestSettings>({})
  /** Published the moment a manifest is adopted, not at the end of the content pipeline — a
   *  rotation must not wait for every element to download (see PlayerEngine.kt). */
  readonly orientation = new Signal<string | null>(null)

  private readonly api: PlayerApi
  private readonly store: TokenStore
  private readonly cache: MediaStore
  private readonly opts: EngineOptions
  private readonly clock: () => number

  private stopped = false
  /** Every pending wait, and whether [nudge] may end it early. */
  private waits = new Map<() => void, boolean>()
  private validUntilMillis: number | null = null
  private deviceTimezone: string | null = null
  private lastAppliedPower: boolean | null = null
  /** When the live manifest last handed us URLs that playback streams from directly. Those URLs
   *  are presigned and expire, so past [STREAM_URL_REFRESH_MILLIS] the next poll asks for a
   *  full manifest instead of a 304. Null when everything plays from the cache. */
  private streamingSince: number | null = null
  private pendingPlays: PlayReport[] = []
  private pendingErrors: string[] = []

  constructor(opts: EngineOptions) {
    this.opts = opts
    this.api = opts.api
    this.store = opts.store
    this.cache = opts.cache
    this.clock = opts.clock ?? Date.now
    this.debug = new Signal<DebugInfo>({
      deviceName: opts.store.name(),
      version: null,
      cachedBytes: 0,
      itemCount: 0,
      lastPollAt: null,
      lastError: null,
      lastErrorAt: null,
      apiHost: opts.apiHost,
      storage: opts.cache.available ? 'offline cache' : 'everything streams (no cache over plain HTTP)',
      schedule: null,
      updateStatus: null,
    })
  }

  async run(): Promise<void> {
    // Alongside the sync loop, not inside it: a scheduled power change has to happen on time
    // even when polling is failing or the network is gone entirely.
    void this.runPowerLoop()
    await this.runForever()
  }

  /** Ends both loops at their next wait. For tests; a screen never stops. */
  stop() {
    this.stopped = true
    for (const wake of Array.from(this.waits.keys())) wake()
  }

  /** Ends the current poll wait early — called when the browser regains its network, the
   *  nearest thing a web screen has to the Android player's MQTT push. */
  nudge() {
    for (const [wake, wakeable] of Array.from(this.waits)) if (wakeable) wake()
  }

  private sleep(ms: number, wakeable = false): Promise<void> {
    return new Promise((resolve) => {
      const done = () => {
        clearTimeout(timer)
        this.waits.delete(done)
        resolve()
      }
      const timer = setTimeout(done, ms)
      this.waits.set(done, wakeable)
    })
  }

  private setError(message: string) {
    this.debug.update((d) => ({ ...d, lastError: message, lastErrorAt: this.clock() }))
  }

  private async runForever() {
    const host = this.opts.apiHost
    let consecutiveFailures = 0
    let unauthorizedStreak = 0

    while (!this.stopped) {
      try {
        const token = this.store.token() ?? (await this.pairUntilClaimed())
        if (!token) continue
        await this.syncAndPlay(token)
        consecutiveFailures = 0
        unauthorizedStreak = 0
      } catch (e) {
        if (this.stopped) return
        if (e instanceof UnauthorizedError) {
          // A single 401 is not enough to throw a pairing away — somebody would have to walk to
          // the screen to redo it. Several in a row, confirmed quickly, is. See PlayerEngine.kt.
          unauthorizedStreak++
          console.warn(TAG, `token rejected (${unauthorizedStreak}/${UNAUTHORIZED_BEFORE_REPAIR})`)
          if (unauthorizedStreak >= UNAUTHORIZED_BEFORE_REPAIR) {
            console.warn(TAG, 'token rejected repeatedly — clearing and re-pairing')
            this.store.clear()
            this.forgetAccountSettings()
            unauthorizedStreak = 0
            consecutiveFailures = 0
            this.state.set({ kind: 'starting' })
          } else {
            if (this.state.value.kind !== 'playing') {
              this.state.set({
                kind: 'trouble',
                deviceName: this.store.name(),
                message: `Server rejected this screen's credential (${unauthorizedStreak} of ${UNAUTHORIZED_BEFORE_REPAIR})`,
                apiHost: host,
                attempts: unauthorizedStreak,
              })
            }
            await this.sleep(UNAUTHORIZED_RETRY_SECONDS * 1000)
          }
        } else {
          console.error(TAG, 'loop error', e)
          consecutiveFailures++
          const message = (e as Error)?.message || String(e)
          this.setError(message)
          // A failed poll must never replace content that is playing — the cached loop is still
          // the best thing to be showing.
          if (this.state.value.kind !== 'playing') {
            this.state.set({
              kind: 'trouble',
              deviceName: this.store.name(),
              message,
              apiHost: host,
              attempts: consecutiveFailures,
            })
          }
          await this.sleep(POLL_SECONDS * 1000, true)
        }
      }
    }
  }

  /** Shows a code and polls until a human claims it. Returns the new device token. */
  private async pairUntilClaimed(): Promise<string | null> {
    const host = this.opts.apiHost
    let pair
    try {
      pair = await this.api.startPairing()
    } catch (e) {
      // No network yet: say so on screen instead of showing a code that cannot work.
      this.state.set({
        kind: 'pairing',
        code: '······',
        apiHost: host,
        error: "Cannot reach the server. Check this screen's network.",
        checks: 0,
      })
      await this.sleep(5_000, true)
      return null
    }

    let checks = 0
    this.state.set({ kind: 'pairing', code: pair.pairing_code, apiHost: host, error: null, checks })

    while (!this.stopped) {
      await this.sleep(pair.poll_seconds * 1000)
      checks++
      let poll
      try {
        poll = await this.api.pollPairing(pair.poll_token)
      } catch (e) {
        this.setError((e as Error).message)
        this.state.set({
          kind: 'pairing', code: pair.pairing_code, apiHost: host, error: 'Lost connection — retrying', checks,
        })
        continue
      }
      // 404 → the code expired. Start over with a fresh one rather than show a stale code.
      if (poll === null) return null

      if (poll.claimed && poll.device_token) {
        this.store.saveToken(poll.device_token, poll.name)
        this.store.saveDeviceId(poll.device_id)
        this.debug.update((d) => ({ ...d, deviceName: poll.name ?? null }))
        // Held briefly so pairing visibly succeeds instead of cutting to black.
        this.state.set({ kind: 'claimed', deviceName: poll.name || 'This screen' })
        await this.sleep(1_500)
        return poll.device_token
      }
      this.state.set({ kind: 'pairing', code: pair.pairing_code, apiHost: host, error: null, checks })
    }
    return null
  }

  /** The steady state: poll, download what changed, play, heartbeat. */
  private async syncAndPlay(token: string) {
    // Play whatever was on screen before the restart, from the cache, before touching the
    // network — a screen coming back from a power cut must show content, not a logo.
    await this.restoreFromDisk()

    while (!this.stopped) {
      const showing = this.state.value.kind === 'playing' || this.state.value.kind === 'idle'
      const urlsExpiring =
        this.streamingSince !== null && this.clock() - this.streamingSince > STREAM_URL_REFRESH_MILLIS
      const etag = showing && !urlsExpiring ? this.store.etag() || null : null
      const manifest = await this.api.fetchManifest(token, etag)

      this.debug.update((d) => ({ ...d, lastPollAt: this.clock() }))

      if (manifest) {
        await this.applyManifest(manifest)
        this.store.saveEtag(`"${manifest.version}"`)
        this.store.saveManifestJson(JSON.stringify(manifest))
      }

      try {
        // Drained before the call: if it fails these are lost rather than resent forever.
        const plays = this.pendingPlays.splice(0)
        const errors = this.pendingErrors.splice(0)
        const reported = this.opts.currentSettings?.() ?? {}
        const res = await this.api.heartbeat(token, {
          app_version: this.opts.appVersion,
          screen: this.opts.screenSize?.() ?? null,
          current_item_id: null,
          errors,
          plays,
          reported_settings: Object.keys(reported).length ? reported : null,
        })
        if (etag !== null && `"${res.version}"` !== etag) {
          // Version moved under us — loop again soon, but never with zero delay.
          await this.sleep(MIN_POLL_MILLIS)
          continue
        }
      } catch (e) {
        if (e instanceof UnauthorizedError) throw e
        console.warn(TAG, 'heartbeat failed (continuing)', e)
      }

      await this.sleep(this.nextPollDelayMillis(), true)
    }
  }

  /** The poll interval — but never sleep past a schedule boundary, so a daypart lands on time. */
  private nextPollDelayMillis(): number {
    const normal = POLL_SECONDS * 1000
    if (this.validUntilMillis === null) return normal
    const untilBoundary = this.validUntilMillis - this.clock()
    if (untilBoundary <= 0) return MIN_POLL_MILLIS
    if (untilBoundary < normal) return Math.max(untilBoundary, MIN_POLL_MILLIS)
    return normal
  }

  /**
   * A screen that has lost its account must stop acting on that account's settings: touch
   * unlocked, no power schedule or override, and awake.
   */
  private forgetAccountSettings() {
    this.settings.set({})
    this.opts.applySettings?.({})
    this.deviceTimezone = null
    if (this.lastAppliedPower === false) {
      try {
        this.opts.applyPower?.(true)
      } catch (e) {
        console.warn(TAG, 'wake after reset failed', e)
      }
    }
    this.lastAppliedPower = null
  }

  private adoptSettings(manifest: Manifest) {
    const settings = manifest.settings ?? {}
    this.deviceTimezone = manifest.device.timezone ?? null
    this.orientation.set(manifest.device.orientation)
    this.settings.set(settings)
    this.opts.applySettings?.(settings)
    // Straight away, not on the next power check: a "Turn off now" lands with its manifest.
    this.evaluatePower()
  }

  private async runPowerLoop() {
    while (!this.stopped) await this.sleep(this.evaluatePower())
  }

  /**
   * Applies the current power decision if it differs from what was last applied, and returns how
   * long to wait before checking again. Once per change, never on every check — a screen woken
   * by hand during scheduled off hours stays on until the next change.
   */
  evaluatePower(): number {
    const settings = this.settings.value
    const now = this.clock()
    const decision = decide(settings.power_schedule, settings.power_override, now, resolveZone(this.deviceTimezone))
    // No decision means nothing is configured — but a screen this process put to sleep must not
    // stay asleep just because the thing that said "off" is gone ("Resume schedule" with no
    // schedule deletes the override, and then nothing would ever say "on"). Same in PlayerEngine.kt.
    const on = decision ? decision.on : this.lastAppliedPower === false ? true : null
    if (on !== null && on !== this.lastAppliedPower) {
      console.info(TAG, `power ${on ? 'on' : 'off'} (${decision?.source ?? 'cleared'})`)
      try {
        this.opts.applyPower?.(on)
      } catch (e) {
        console.warn(TAG, 'power apply failed', e)
      }
      this.lastAppliedPower = on
    }
    const untilChange = decision?.nextChangeMillis != null ? decision.nextChangeMillis - now : null
    if (untilChange === null) return POWER_CHECK_MILLIS
    if (untilChange <= 0) return MIN_POLL_MILLIS
    return Math.min(untilChange, POWER_CHECK_MILLIS)
  }

  /** Restores the last manifest and plays whatever of it is already cached. Never downloads. */
  private async restoreFromDisk() {
    if (this.state.value.kind === 'playing') return
    const stored = this.store.manifestJson()
    if (!stored) return
    let manifest: Manifest
    try {
      manifest = JSON.parse(stored)
    } catch (e) {
      console.warn(TAG, 'stored manifest unreadable, ignoring', e)
      return
    }

    const playable: ManifestSlot[] = []
    for (const slot of effectiveSlots(manifest)) {
      if (await this.allCached(slot.elements)) playable.push(slot)
    }
    if (!playable.length) return

    console.info(TAG, `restored ${playable.length} cached slots`)
    this.state.set({
      kind: 'playing',
      slots: playable,
      shuffle: manifest.playlist?.shuffle ?? false,
      sources: await this.sourcesFor(playable, new Set()),
    })
    // A stored manifest's addresses may have expired while the screen was off: a video without a
    // stored copy plays from one, so it gets a fresh manifest on the very first poll.
    if (this.streamsAnything(playable, new Set())) this.streamingSince = 0
    this.debug.update((d) => ({
      ...d,
      deviceName: manifest.device.name,
      version: manifest.version,
      itemCount: playable.length,
      schedule: manifest.schedule_name ?? null,
    }))
    // A restarting screen comes back at its configured settings and power immediately.
    this.adoptSettings(manifest)
  }

  /** The file this element keeps on the screen, if any — see [storedFile]. */
  private stored(el: ManifestElement): StoredFile | null {
    return storedFile(el, this.opts.canPlayStream ?? (() => false))
  }

  private async allCached(elements: ManifestElement[]): Promise<boolean> {
    for (const el of elements) {
      const file = this.stored(el)
      if (file && !(await this.cache.isCached(file.checksum, file.bytes))) return false
    }
    return true
  }

  /** Keyed by the element's own checksum, which is what playback looks up. A stored video's
   *  value is prefixed [STREAM_SOURCE_PREFIX]: it is fed to MediaSource, never set as `src`. */
  private async sourcesFor(slots: ManifestSlot[], unstored: Set<string>): Promise<Record<string, string>> {
    const sources: Record<string, string> = {}
    for (const el of slots.flatMap((s) => s.elements)) {
      if (sources[el.checksum]) continue
      const file = this.stored(el)
      if (!file || unstored.has(file.checksum)) {
        sources[el.checksum] = el.url
      } else {
        const url = await this.cache.objectUrl(file.checksum)
        sources[el.checksum] = el.kind === 'video' ? STREAM_SOURCE_PREFIX + url : url
      }
    }
    return sources
  }

  /** Presigned addresses expire; anything playing from one needs the manifest refreshed in time. */
  private streamsAnything(slots: ManifestSlot[], unstored: Set<string>): boolean {
    return unstored.size > 0 || slots.some((s) => s.elements.some((el) => el.kind === 'video' && !this.stored(el)))
  }

  private async applyManifest(manifest: Manifest) {
    this.validUntilMillis = parseInstantMillis(manifest.valid_until)
    this.adoptSettings(manifest)

    const deviceName = manifest.device.name
    const slots = effectiveSlots(manifest)
    this.debug.update((d) => ({
      ...d,
      deviceName,
      version: manifest.version,
      itemCount: slots.reduce((n, s) => n + s.elements.length, 0),
      schedule: manifest.schedule_name ?? null,
    }))

    if (!slots.length) {
      this.state.set({ kind: 'idle', deviceName })
      this.streamingSince = null
      await this.cache.evictExcept([])
      await this.refreshCachedBytes()
      return
    }

    // Download everything missing BEFORE switching over, so the screen never shows a gap while a
    // file is still arriving.
    const all = slots.flatMap((s) => s.elements)
    const files: StoredFile[] = []
    for (const el of all) {
      const file = this.stored(el)
      if (file && !files.some((f) => f.checksum === file.checksum)) files.push(file)
    }
    // Stored files that couldn't be stored after all, and so play from their address.
    const streamed = new Set<string>()
    const missing: StoredFile[] = []
    if (this.cache.available) {
      for (const file of files) {
        if (!(await this.cache.isCached(file.checksum, file.bytes))) missing.push(file)
      }
    } else {
      // Nowhere to keep a file: everything plays from its address, and nothing is announced as
      // "preparing" because nothing is being prepared.
      for (const file of files) streamed.add(file.checksum)
    }

    let fetched = 0
    for (const file of missing) {
      this.state.set({
        kind: 'preparing', deviceName, done: fetched, total: missing.length,
        currentFile: `${file.kind} · ${Math.floor(file.bytes / 1_048_576)} MB`,
      })
      try {
        console.info(TAG, `downloading ${file.checksum} (${file.bytes} bytes)`)
        await this.cache.download(file.checksum, file.url, file.bytes)
      } catch (e) {
        // Where Android skips a slot whose file failed to download, a browser has a better
        // option: play it straight from its address. The usual cause here is storage the
        // browser refused (quota) or a bucket that doesn't allow this origin to read it, and
        // neither is a reason for a blank slot while the network is up.
        console.error(TAG, `download failed for ${file.checksum}; streaming it instead`, e)
        this.setError(`download: ${(e as Error).message} — streaming instead`)
        streamed.add(file.checksum)
      }
      fetched++
    }
    this.streamingSince = this.streamsAnything(slots, streamed) ? this.clock() : null

    const sources = await this.sourcesFor(slots, streamed)

    // Warm what is about to go on screen before switching, so the first loop through new content
    // looks like every loop after it.
    const seen = new Set<string>()
    for (const el of all) {
      if (el.kind !== 'image' || seen.has(el.checksum)) continue
      seen.add(el.checksum)
      if (missing.length) {
        this.state.set({ kind: 'preparing', deviceName, done: missing.length, total: missing.length, currentFile: `getting ${el.kind} ready` })
      }
      try {
        await this.opts.warmMedia?.(sources[el.checksum], el.kind)
      } catch (e) {
        console.warn(TAG, `warm-up failed for ${el.id}`, e)
      }
    }

    this.state.set({ kind: 'playing', slots, shuffle: manifest.playlist?.shuffle ?? false, sources })

    // Evict only after the new set is safely stored.
    await this.cache.evictExcept(files.filter((f) => !streamed.has(f.checksum)).map((f) => f.checksum))
    await this.refreshCachedBytes()
  }

  private async refreshCachedBytes() {
    const cachedBytes = await this.cache.cachedBytes().catch(() => 0)
    this.debug.update((d) => ({ ...d, cachedBytes }))
  }

  /** Called by playback each time a slot finishes — once per element it contained. */
  reportPlay(slot: ManifestSlot, startedAtMillis: number, seconds: number) {
    for (const el of slot.elements) {
      if (this.pendingPlays.length >= MAX_PENDING_PLAYS) this.pendingPlays.shift()
      this.pendingPlays.push({
        media_id: el.media_id ?? null,
        // Blank on purpose: the server resolves the name from media_id. A website has none.
        filename: el.kind === KIND_WEB ? el.url.slice(0, 255) : '',
        started_at: new Date(startedAtMillis).toISOString(),
        seconds: Math.max(0, seconds),
      })
    }
  }

  reportError(message: string) {
    if (this.pendingErrors.length >= MAX_PENDING_ERRORS) this.pendingErrors.shift()
    this.pendingErrors.push(message.slice(0, 500))
    this.setError(message)
  }

  setUpdateStatus(status: string) {
    this.debug.update((d) => ({ ...d, updateStatus: status }))
  }
}

export interface StoredFile {
  kind: string
  checksum: string
  url: string
  bytes: number
}

/** Marks a source that playback must feed to MediaSource rather than set as a video's `src`. */
export const STREAM_SOURCE_PREFIX = 'mse:'

/**
 * The file an element keeps on the screen for offline play, or null when it only ever plays from
 * its address.
 *
 * - A picture: the file itself.
 * - A website: nothing — it loads live.
 * - A video: its streaming copy (fragmented MP4, made at upload by the backend's
 *   services/video_streams.py), fed to the browser through Media Source Extensions. Never the
 *   original: a smart TV's browser hands a plain video file to the TV's own player, which can't
 *   open one stored inside the browser — a black screen on a Samsung Tizen TV. MediaSource is
 *   what TV browsers do play from memory (it's how YouTube runs on them). A video whose copy
 *   isn't ready yet, or whose codecs this browser's MediaSource refuses, plays from its address.
 */
export function storedFile(el: ManifestElement, canPlayStream: (mime: string) => boolean): StoredFile | null {
  if (el.kind === KIND_WEB) return null
  if (el.kind === 'video') {
    if (!el.stream_url || !el.stream_checksum || !el.stream_bytes || !el.stream_mime) return null
    if (!canPlayStream(el.stream_mime)) return null
    return { kind: el.kind, checksum: el.stream_checksum, url: el.stream_url, bytes: el.stream_bytes }
  }
  return { kind: el.kind, checksum: el.checksum, url: el.url, bytes: el.bytes }
}

/** Prefers the real multi-element slots, falling back to one-element slots built from `items`
 *  when a backend predates `slots`. */
export function effectiveSlots(manifest: Manifest): ManifestSlot[] {
  if (manifest.slots?.length) return manifest.slots
  return (manifest.items ?? []).map((item) => ({
    id: item.id,
    duration_seconds: item.duration_seconds,
    elements: [
      {
        id: item.id, media_id: item.media_id, kind: item.kind, url: item.url, checksum: item.checksum,
        bytes: item.bytes, fit: item.fit, has_audio: item.has_audio,
      },
    ],
  }))
}

/** No push reaches a browser (see the file header), so this is shorter than Android's 30s. A
 *  poll with nothing new is a 304 of a few hundred bytes. */
export const POLL_SECONDS = 10
/** Never poll faster than this, whatever a boundary says. */
export const MIN_POLL_MILLIS = 2_000
/** How often power is re-checked when no change is due sooner. */
export const POWER_CHECK_MILLIS = 30_000
/** Consecutive 401s before a screen gives up its pairing. */
export const UNAUTHORIZED_BEFORE_REPAIR = 3
export const UNAUTHORIZED_RETRY_SECONDS = 5
/** Presigned media URLs live 6 hours; refresh well inside that when anything streams. */
export const STREAM_URL_REFRESH_MILLIS = 4 * 60 * 60 * 1000
export const MAX_PENDING_PLAYS = 50
export const MAX_PENDING_ERRORS = 20
