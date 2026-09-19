/**
 * The backend's device-sync contract — the same four calls, and the same JSON, as the Android
 * player's `api/Models.kt` and `api/ApiClient.kt`. Field names match the wire exactly.
 *
 * Every field added after the first release is optional here for the reason Models.kt gives:
 * a screen must keep playing against a backend a deploy or two behind.
 */

export interface PairStartResponse {
  device_id: string
  pairing_code: string
  poll_token: string
  expires_at: string
  poll_seconds: number
}

export interface PairPollResponse {
  claimed: boolean
  device_id: string
  /** Present exactly once, on the first poll after a human claims the screen. */
  device_token?: string | null
  name?: string | null
}

export interface ManifestElement {
  id: string
  media_id?: string | null
  /** "image", "video", "web" — a website loaded live from `url`, nothing to download — or
   *  "text", drawn from `text` and `text_style` (url is empty). */
  kind: string
  url: string
  checksum: string
  bytes: number
  text?: string | null
  text_style?: TextStyle | null
  x?: number
  y?: number
  width?: number
  height?: number
  fit?: string
  has_audio?: boolean
  rotation_degrees?: number
  /** A video's streaming copy — fragmented MP4 made at upload, played through MediaSource. See
   *  `storedFile` in engine.ts. Absent until the backend has made it, and for anything else. */
  stream_url?: string | null
  stream_bytes?: number | null
  stream_checksum?: string | null
  /** Includes codecs, e.g. `video/mp4; codecs="avc1.64001f,mp4a.40.2"`. */
  stream_mime?: string | null
  /** A video's thumbnail — what a blurred scene background shows for it. */
  poster_url?: string | null
}

export const KIND_WEB = 'web'
/** Text drawn by the player itself, from `text` and `text_style`. Nothing to download. */
export const KIND_TEXT = 'text'

/** How a text element looks — the backend's TextStyle. `size` is a fraction of the screen's
 *  height, so a scene reads the same on every panel. Always complete for a text element. */
export interface TextStyle {
  size: number
  color: string
  weight: 'regular' | 'bold'
  align: 'left' | 'center' | 'right'
  background: string | null
}

export interface ManifestSlot {
  id: string
  duration_seconds: number
  elements: ManifestElement[]
  /** "black" (the default, also for a backend that predates it) or "blur" — see
   *  sceneBackground.ts. */
  background?: string
  /** With background "color": the #RRGGBB behind the scene. */
  background_color?: string | null
}

export interface ManifestItem {
  id: string
  media_id?: string | null
  kind: string
  url: string
  checksum: string
  bytes: number
  duration_seconds: number
  fit?: string
  has_audio?: boolean
}

export interface PowerSchedule {
  enabled?: boolean
  /** Bit 0 = Monday. */
  days_of_week?: number
  power_on?: string
  power_off?: string
}

export interface PowerOverride {
  state: string
  /** ISO-8601 UTC, or null for no end — which only counts while there is no schedule. */
  until?: string | null
}

export interface ManifestSettings {
  /** 0-100, applied to every video that carries sound. */
  volume?: number | null
  /** Swallows every touch and click on the player — see ui/input.ts. */
  touchscreen_disabled?: boolean | null
  power_schedule?: PowerSchedule | null
  power_override?: PowerOverride | null
}

export interface Manifest {
  version: string
  /** `orientation` is the old portrait/landscape word; `rotation` (0/90/180/270, clockwise)
   *  is what newer backends send and what the stage is actually turned by. */
  device: { name: string; orientation: string; rotation?: number | null; timezone?: string | null }
  /** null is a valid state — a newly paired screen with nothing assigned yet. */
  playlist?: { id: string; name: string; shuffle: boolean } | null
  items?: ManifestItem[]
  slots?: ManifestSlot[]
  schedule_name?: string | null
  valid_until?: string | null
  settings?: ManifestSettings
}

export interface PlayReport {
  media_id?: string | null
  filename: string
  started_at: string
  seconds: number
}

export interface HeartbeatRequest {
  app_version?: string | null
  screen?: { width: number; height: number } | null
  current_item_id?: string | null
  errors: string[]
  plays: PlayReport[]
  reported_settings?: Record<string, string | number | boolean> | null
  /** Playback health — frames dropped since the last beat, the decoder (unknown in a browser),
   *  and the last measured download speed. See PlayerEngine.kt's PlaybackReport. */
  playback?: { dropped_frames: number; decoder: string | null; download_bytes_per_second: number | null } | null
}

export interface HeartbeatResponse {
  version: string
  /** Always null for a web screen — the backend offers APKs to Android screens only. */
  update?: { version: string; url: string } | null
}

/** Raised when the server rejects our device token — the screen may have to re-pair. */
export class UnauthorizedError extends Error {
  constructor() {
    super('device token rejected')
    this.name = 'UnauthorizedError'
  }
}

/** Raised on 410: someone in the CMS disconnected this screen. Unlike a 401, which can be a
 *  transient fault worth riding out, this is deliberate and final — the screen resets at once. */
export class DisconnectedError extends Error {
  constructor() {
    super('disconnected from the CMS')
    this.name = 'DisconnectedError'
  }
}

export interface PlayerApi {
  startPairing(): Promise<PairStartResponse>
  /** Null when the pairing expired or was already collected (HTTP 404). */
  pollPairing(pollToken: string): Promise<PairPollResponse | null>
  /** Null when the server answered 304 — nothing changed. */
  fetchManifest(token: string, etag: string | null): Promise<Manifest | null>
  heartbeat(token: string, body: HeartbeatRequest): Promise<HeartbeatResponse>
}

/** Venue wifi is frequently awful; a slow answer beats a failed one, but a hung request must
 *  not freeze the loop forever either. */
const REQUEST_TIMEOUT_MS = 30_000

async function request(url: string, init: RequestInit = {}): Promise<Response> {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timer = controller ? setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS) : null
  try {
    return await fetch(url, { ...init, cache: 'no-store', signal: controller?.signal })
  } catch (e) {
    throw new Error(controller?.signal.aborted ? `request timed out: ${url}` : `network error: ${(e as Error).message}`)
  } finally {
    if (timer) clearTimeout(timer)
  }
}

export class ApiClient implements PlayerApi {
  /** `/api` in production: server.mjs proxies it to the backend on this same origin. */
  constructor(private readonly baseUrl = '/api') {}

  async startPairing(): Promise<PairStartResponse> {
    const res = await request(`${this.baseUrl}/devices/pair`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // The one thing that differs from the Android player: the CMS records which player this is.
      body: JSON.stringify({ platform: 'web' }),
    })
    if (!res.ok) throw new Error(`pair failed: HTTP ${res.status}`)
    return res.json()
  }

  async pollPairing(pollToken: string): Promise<PairPollResponse | null> {
    const res = await request(`${this.baseUrl}/devices/pair/${encodeURIComponent(pollToken)}`)
    if (res.status === 404) return null
    if (!res.ok) throw new Error(`poll failed: HTTP ${res.status}`)
    return res.json()
  }

  async fetchManifest(token: string, etag: string | null): Promise<Manifest | null> {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
    if (etag) headers['If-None-Match'] = etag
    const res = await request(`${this.baseUrl}/device/manifest`, { headers })
    if (res.status === 304) return null
    if (res.status === 401) throw new UnauthorizedError()
    if (res.status === 410) throw new DisconnectedError()
    if (!res.ok) throw new Error(`manifest failed: HTTP ${res.status}`)
    return res.json()
  }

  async heartbeat(token: string, body: HeartbeatRequest): Promise<HeartbeatResponse> {
    const res = await request(`${this.baseUrl}/device/heartbeat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (res.status === 401) throw new UnauthorizedError()
    if (res.status === 410) throw new DisconnectedError()
    if (!res.ok) throw new Error(`heartbeat failed: HTTP ${res.status}`)
    return res.json()
  }
}
