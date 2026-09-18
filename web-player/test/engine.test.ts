/**
 * The loop, driven with fakes on virtual time — the scenarios of the Android player's
 * PlayerEngineTest.kt and PlayerPowerTest.kt, so both players are held to the same behaviour.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  DisconnectedError,
  UnauthorizedError,
  type HeartbeatRequest,
  type Manifest,
  type ManifestSettings,
  type PairPollResponse,
  type PlayerApi,
} from '../src/api'
import { PlayerEngine, POLL_SECONDS } from '../src/engine'
import type { MediaStore } from '../src/mediaCache'
import type { TokenStore } from '../src/store'

class FakeStore implements TokenStore {
  data: Record<string, string> = {}
  token() { return this.data.token ?? null }
  etag() { return this.data.etag ?? null }
  name() { return this.data.name ?? null }
  saveToken(token: string, name: string | null | undefined) { this.data.token = token; if (name != null) this.data.name = name }
  saveEtag(etag: string) { this.data.etag = etag }
  manifestJson() { return this.data.manifest ?? null }
  saveManifestJson(json: string) { this.data.manifest = json }
  deviceId() { return this.data.deviceId ?? null }
  saveDeviceId(id: string) { this.data.deviceId = id }
  clear() { this.data = {} }
}

class FakeCache implements MediaStore {
  available = true
  files = new Map<string, number>()
  failing = new Set<string>()
  log: string[] = []
  async isCached(checksum: string, bytes: number) { return this.files.get(checksum) === bytes }
  async download(checksum: string, _url: string, bytes: number, onProgress?: (n: number) => void) {
    onProgress?.(Math.floor(bytes / 2))
    onProgress?.(bytes)
    this.log.push(`download ${checksum}`)
    if (this.failing.has(checksum)) throw new Error('boom')
    this.files.set(checksum, bytes)
  }
  async objectUrl(checksum: string) { return `blob:${checksum}` }
  async evictExcept(keep: Iterable<string>) {
    const k = new Set(keep)
    this.log.push(`evict except ${[...k].sort().join(',')}`)
    for (const c of [...this.files.keys()]) if (!k.has(c)) this.files.delete(c)
  }
  async cachedBytes() { return [...this.files.values()].reduce((a, b) => a + b, 0) }
}

class FakeApi implements PlayerApi {
  pairs = 0
  pollAnswers: Array<PairPollResponse | null | Error> = []
  pairError: Error | null = null
  manifest: Manifest | null = null
  manifestError: Error | null = null
  heartbeats: HeartbeatRequest[] = []
  manifestCalls: Array<string | null> = []

  async startPairing() {
    if (this.pairError) throw this.pairError
    this.pairs++
    return { device_id: 'dev-1', pairing_code: `CODE${this.pairs}`, poll_token: 'poll', expires_at: '', poll_seconds: 5 }
  }
  async pollPairing() {
    const next = this.pollAnswers.length ? this.pollAnswers.shift()! : { claimed: false, device_id: 'dev-1' }
    if (next instanceof Error) throw next
    return next
  }
  async fetchManifest(_token: string, etag: string | null) {
    this.manifestCalls.push(etag)
    if (this.manifestError) throw this.manifestError
    if (etag && this.manifest && etag === `"${this.manifest.version}"`) return null
    return this.manifest
  }
  async heartbeat(_token: string, body: HeartbeatRequest) {
    if (this.manifestError instanceof UnauthorizedError || this.manifestError instanceof DisconnectedError) throw this.manifestError
    this.heartbeats.push(body)
    return { version: this.manifest?.version ?? 'v0', update: null }
  }
}

function manifest(overrides: Partial<Manifest> = {}, settings: ManifestSettings = {}): Manifest {
  return {
    version: 'v1',
    device: { name: 'Lobby', orientation: 'landscape', timezone: 'Asia/Jakarta' },
    playlist: { id: 'p', name: 'Loop', shuffle: false },
    slots: [
      { id: 's1', duration_seconds: 10, elements: [{ id: 'e1', media_id: 'm1', kind: 'image', url: 'https://r2/a', checksum: 'a', bytes: 100 }] },
      { id: 's2', duration_seconds: 10, elements: [{ id: 'e2', media_id: 'm2', kind: 'video', url: 'https://r2/b', checksum: 'b', bytes: 200 }] },
    ],
    settings,
    ...overrides,
  }
}

let api: FakeApi
let store: FakeStore
let cache: FakeCache
let power: boolean[]
let engine: PlayerEngine

function start(extra: Partial<ConstructorParameters<typeof PlayerEngine>[0]> = {}) {
  engine = new PlayerEngine({
    api, store, cache, appVersion: 'web-test', apiHost: 'api.example.com',
    applyPower: (on) => power.push(on),
    ...extra,
  })
  void engine.run()
  return engine
}

const tick = (ms: number) => vi.advanceTimersByTimeAsync(ms)

beforeEach(() => {
  // Monday 2026-09-07 10:00 in Jakarta.
  vi.useFakeTimers({ now: Date.UTC(2026, 8, 7, 3) })
  api = new FakeApi()
  store = new FakeStore()
  cache = new FakeCache()
  power = []
})

afterEach(() => {
  engine?.stop()
  vi.useRealTimers()
})

describe('pairing', () => {
  it('an unpaired screen shows a code and names its server', async () => {
    start()
    await tick(0)
    expect(engine.state.value).toMatchObject({ kind: 'pairing', code: 'CODE1', apiHost: 'api.example.com' })
  })

  it('waiting shows it is alive rather than frozen', async () => {
    start()
    await tick(10_000)
    expect(engine.state.value).toMatchObject({ kind: 'pairing', checks: 2 })
  })

  it('when a human claims it, the token is stored and success is shown', async () => {
    api.pollAnswers = [{ claimed: true, device_id: 'dev-1', device_token: 'tok', name: 'Lobby' }]
    start()
    await tick(5_000)
    expect(store.token()).toBe('tok')
    expect(store.deviceId()).toBe('dev-1')
    expect(engine.state.value).toEqual({ kind: 'claimed', deviceName: 'Lobby' })
  })

  it('an expired code is replaced rather than shown forever', async () => {
    api.pollAnswers = [null]
    start()
    await tick(5_000)
    expect(engine.state.value).toMatchObject({ kind: 'pairing', code: 'CODE2' })
  })

  it('no network during pairing says so instead of showing an unusable code', async () => {
    api.pairError = new Error('offline')
    start()
    await tick(0)
    expect(engine.state.value).toMatchObject({ kind: 'pairing', code: '······' })
    expect((engine.state.value as { error: string }).error).toMatch(/Cannot reach the server/)
  })
})

describe('sync', () => {
  beforeEach(() => {
    store.saveToken('tok', 'Lobby')
  })

  it('content downloads before it is shown, and eviction happens after', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    expect(engine.state.value.kind).toBe('playing')
    expect(cache.log).toEqual(['download a', 'evict except a'])
    const s = engine.state.value as Extract<typeof engine.state.value, { kind: 'playing' }>
    expect(s.sources).toEqual({ a: 'blob:a', b: 'https://r2/b' })
  })

  it('a picture that fails to download streams from its address instead of leaving a gap', async () => {
    api.manifest = manifest()
    cache.failing.add('a')
    start()
    await tick(0)
    const s = engine.state.value as Extract<typeof engine.state.value, { kind: 'playing' }>
    expect(s.slots.map((x) => x.id)).toEqual(['s1', 's2'])
    expect(s.sources.a).toBe('https://r2/a')
    expect(cache.log).toContain('evict except ')
  })

  it('a video with a streaming copy stores the copy, not the original, and plays it through MediaSource', async () => {
    const m = manifest()
    Object.assign(m.slots![1].elements[0], {
      stream_url: 'https://r2/b-stream', stream_bytes: 180, stream_checksum: 'sha256:bs', stream_mime: 'video/mp4; codecs="avc1.64001f"',
    })
    api.manifest = m
    start({ canPlayStream: () => true })
    await tick(0)
    expect(cache.log).toEqual(['download a', 'download sha256:bs', 'evict except a,sha256:bs'])
    const s = engine.state.value as Extract<typeof engine.state.value, { kind: 'playing' }>
    expect(s.sources).toEqual({ a: 'blob:a', b: 'mse:blob:sha256:bs' })
  })

  it('a streaming copy this browser cannot play is not stored; the video plays from its address', async () => {
    const m = manifest()
    Object.assign(m.slots![1].elements[0], {
      stream_url: 'https://r2/b-stream', stream_bytes: 180, stream_checksum: 'sha256:bs', stream_mime: 'video/mp4; codecs="hev1"',
    })
    api.manifest = m
    start({ canPlayStream: () => false })
    await tick(0)
    expect(cache.log.filter((l) => l.startsWith('download'))).toEqual(['download a'])
    const s = engine.state.value as Extract<typeof engine.state.value, { kind: 'playing' }>
    expect(s.sources.b).toBe('https://r2/b')
  })

  it('a video without a streaming copy yet is not downloaded: it plays from its address, and keeps the manifest fresh', async () => {
    api.manifest = manifest()
    store.saveEtag('"v1"')
    start()
    await tick(0)
    expect(cache.log.filter((l) => l.startsWith('download'))).toEqual(['download a'])
    // Presigned addresses expire: after 4h the next poll asks for a whole manifest, not a 304.
    const calls = api.manifestCalls.length
    await tick(4 * 60 * 60 * 1000 + POLL_SECONDS * 1000)
    expect(api.manifestCalls.slice(calls)).toContain(null)
  })

  it('a restarted screen with a video in its loop fetches fresh addresses on the first poll', async () => {
    store.saveManifestJson(JSON.stringify(manifest()))
    store.saveEtag('"v1"')
    cache.files.set('a', 100)
    api.manifest = manifest()
    start()
    await tick(0)
    expect(api.manifestCalls[0]).toBeNull()
  })

  it('an error stays on the debug overlay after later polls succeed', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    engine.reportError('video broke')
    await tick(POLL_SECONDS * 1000 * 2)
    expect(engine.debug.value.lastError).toBe('video broke')
  })

  it('a blurred scene whose largest element is a video stores its thumbnail for the background', async () => {
    const m = manifest()
    Object.assign(m.slots![1], { background: 'blur' })
    Object.assign(m.slots![1].elements[0], { poster_url: 'https://r2/b-thumb' })
    api.manifest = m
    start()
    await tick(0)
    expect(cache.log).toContain('download poster:b')
    const s = engine.state.value as Extract<typeof engine.state.value, { kind: 'playing' }>
    expect(s.sources['poster:b']).toBe('blob:poster:b')
  })

  it('a black scene stores no thumbnail', async () => {
    const m = manifest()
    Object.assign(m.slots![1].elements[0], { poster_url: 'https://r2/b-thumb' })
    api.manifest = m
    start()
    await tick(0)
    expect(cache.log.some((l) => l.includes('poster'))).toBe(false)
  })

  it('a website element plays without downloading anything', async () => {
    api.manifest = manifest({
      slots: [{ id: 'w', duration_seconds: 30, elements: [{ id: 'we', kind: 'web', url: 'https://example.com', checksum: 'web-x', bytes: 0 }] }],
    })
    start()
    await tick(0)
    expect(engine.state.value).toMatchObject({ kind: 'playing', sources: { 'web-x': 'https://example.com' } })
    expect(cache.log.filter((l) => l.startsWith('download'))).toEqual([])
  })

  it('a screen with no playlist idles rather than erroring', async () => {
    api.manifest = manifest({ playlist: null, slots: [] })
    start()
    await tick(0)
    expect(engine.state.value).toEqual({ kind: 'idle', deviceName: 'Lobby' })
  })

  it('orientation reaches the UI as soon as the manifest is adopted', async () => {
    api.manifest = manifest({ device: { name: 'Lobby', orientation: 'portrait' } })
    start()
    await tick(0)
    expect(engine.orientation.value).toBe('portrait')
  })

  it('a 304 leaves the current content alone', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    const before = engine.state.value
    await tick(POLL_SECONDS * 1000)
    expect(api.manifestCalls).toEqual([null, '"v1"'])
    expect(engine.state.value).toBe(before)
  })

  it('a restarted screen plays from its cache before touching the network', async () => {
    const m = manifest()
    store.saveManifestJson(JSON.stringify(m))
    store.saveEtag('"v1"')
    cache.files.set('a', 100)
    api.manifestError = new Error('offline')
    start()
    await tick(0)
    expect(engine.state.value).toMatchObject({ kind: 'playing', slots: m.slots })
  })

  it('a paired screen that cannot sync shows trouble, never hangs on the splash', async () => {
    api.manifestError = new Error('HTTP 502')
    start()
    await tick(0)
    expect(engine.state.value).toMatchObject({ kind: 'trouble', deviceName: 'Lobby', message: 'HTTP 502', attempts: 1 })
  })

  it('trouble does not replace content that is already playing', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    api.manifestError = new Error('HTTP 502')
    await tick(POLL_SECONDS * 1000)
    expect(engine.state.value.kind).toBe('playing')
  })

  it('dropped frames ride the next heartbeat as a delta', async () => {
    api.manifest = manifest()
    let dropped = 4
    start({ droppedFrames: () => { const d = dropped; dropped = 0; return d } })
    // The first heartbeat goes out with the first manifest, and takes the count with it.
    await tick(0)
    expect(api.heartbeats.slice(-1)[0]!.playback).toEqual({ dropped_frames: 4, decoder: null, download_bytes_per_second: null })
    expect(engine.debug.value.droppedFrames).toBe(4)
    await tick(POLL_SECONDS * 1000)
    expect(api.heartbeats.slice(-1)[0]!.playback?.dropped_frames).toBe(0)
    expect(engine.debug.value.droppedFrames).toBe(4)
  })

  it('rotation in degrees wins over the old orientation word when both are sent', async () => {
    api.manifest = manifest({ device: { name: 'Lobby', orientation: 'portrait', rotation: 270, timezone: 'Asia/Jakarta' } })
    start()
    await tick(0)
    expect(engine.orientation.value).toBe('270')
    api.manifest = manifest({ device: { name: 'Lobby', orientation: 'landscape', timezone: 'Asia/Jakarta' } })
    api.manifest.version = 'v2'
    await tick(POLL_SECONDS * 1000)
    expect(engine.orientation.value).toBe('landscape')
  })

  it('one 401 does not unpair a working screen', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    api.manifestError = new UnauthorizedError()
    await tick(POLL_SECONDS * 1000)
    api.manifestError = null
    await tick(10_000)
    expect(store.token()).toBe('tok')
  })

  it('a screen the CMS disconnects re-pairs at once and forgets the account', async () => {
    // 410 is deliberate, unlike a 401 — no three-strikes wait, and nothing of the old account
    // survives: token, cached content, pending reports, orientation.
    api.manifest = manifest()
    start()
    await tick(0)
    expect(engine.state.value.kind).toBe('playing')
    engine.reportError('stale')
    api.manifestError = new DisconnectedError()
    await tick(POLL_SECONDS * 1000)
    api.manifestError = null
    await tick(1_000)
    expect(store.token()).toBeNull()
    expect(cache.log[cache.log.length - 1]).toBe('evict except ')
    expect(engine.orientation.value).toBeNull()
    expect(engine.state.value.kind).toBe('pairing')
  })

  it('repeated 401s do unpair, within seconds', async () => {
    api.manifestError = new UnauthorizedError()
    start()
    await tick(12_000)
    expect(store.token()).toBeNull()
    expect(engine.state.value.kind).toBe('pairing')
  })

  it('plays are batched onto the next heartbeat, and drained', async () => {
    api.manifest = manifest()
    start()
    await tick(0)
    const slot = api.manifest.slots![0]
    engine.reportPlay(slot, Date.now() - 10_000, 10)
    engine.reportError('bad file')
    await tick(POLL_SECONDS * 1000)
    const beat = api.heartbeats.slice(-1)[0]!
    expect(beat.plays).toEqual([{ media_id: 'm1', filename: '', started_at: new Date(Date.now() - 20_000).toISOString(), seconds: 10 }])
    expect(beat.errors).toEqual(['bad file'])
    expect(beat.app_version).toBe('web-test')
    await tick(POLL_SECONDS * 1000)
    expect(api.heartbeats.slice(-1)[0]!.plays).toEqual([])
  })
})

describe('power', () => {
  beforeEach(() => {
    store.saveToken('tok', 'Lobby')
  })

  const weekdays = { enabled: true, days_of_week: 0b0011111, power_on: '08:00', power_off: '22:00' }

  it('a schedule wakes the screen, then puts it to sleep at the off time', async () => {
    api.manifest = manifest({}, { power_schedule: weekdays })
    start()
    await tick(0)
    expect(power).toEqual([true])
    await tick(12 * 60 * 60 * 1000) // 10:00 → 22:00 Jakarta
    expect(power).toEqual([true, false])
  })

  it('an override arriving in a new manifest applies straight away', async () => {
    api.manifest = manifest({}, { power_schedule: weekdays })
    start()
    await tick(0)
    api.manifest = manifest(
      { version: 'v2' },
      { power_schedule: weekdays, power_override: { state: 'off', until: new Date(Date.now() + 3_600_000).toISOString() } },
    )
    await tick(POLL_SECONDS * 1000)
    expect(power).toEqual([true, false])
  })

  it('resuming with no schedule wakes a screen that was turned off', async () => {
    api.manifest = manifest({}, { power_override: { state: 'off' } })
    start()
    await tick(0)
    expect(power).toEqual([false])
    // "Resume schedule" with no schedule: the override is deleted, and nothing is left.
    api.manifest = manifest({ version: 'v2' }, {})
    await tick(POLL_SECONDS * 1000)
    expect(power).toEqual([false, true])
  })

  it('the same decision is not re-applied on every check', async () => {
    api.manifest = manifest({}, { power_schedule: weekdays })
    start()
    await tick(5 * 60 * 1000)
    expect(power).toEqual([true])
  })

  it('a deleted screen forgets its touch lock and power plan, and wakes up', async () => {
    const applied: ManifestSettings[] = []
    api.manifest = manifest({}, { touchscreen_disabled: true, power_override: { state: 'off' } })
    start({ applySettings: (s) => applied.push(s) })
    await tick(0)
    expect(power).toEqual([false])
    api.manifestError = new UnauthorizedError()
    await tick(POLL_SECONDS * 1000 + 12_000)
    expect(store.token()).toBeNull()
    expect(power).toEqual([false, true])
    expect(engine.settings.value).toEqual({})
    expect(applied.slice(-1)[0]).toEqual({})
  })

  it('a screen with no power configured is never touched', async () => {
    api.manifest = manifest()
    start()
    await tick(60_000)
    expect(power).toEqual([])
  })
})
