/** Response types mirroring the backend's Pydantic models. */

export type UserRole = 'owner' | 'manager'

export interface UserRead {
  id: string
  username: string
  email: string | null
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AccountRead {
  id: string
  name: string
  /** IANA name newly paired screens start in (Settings → General). */
  default_timezone: string
}

export interface MeResponse {
  user: UserRead
  account: AccountRead
  /** null means "every device in the account" — an owner is not scoped by grant rows. */
  device_ids: string[] | null
}

export interface SignupBody {
  username: string
  password: string
  display_name: string
  email?: string | null
  account_name?: string | null
  /** IANA name — becomes the account's default timezone. Omitted means UTC. */
  timezone?: string | null
}

export interface LoginBody {
  identifier: string
  password: string
}

// --- Media ---

export type MediaKind = 'image' | 'video'

export interface MediaRead {
  id: string
  filename: string
  kind: MediaKind
  mime_type: string
  size_bytes: number
  width: number | null
  height: number | null
  duration_seconds: number | null
  checksum: string
  created_at: string
  created_by: string | null
  thumbnail_url: string | null
  /** Presigned full-resolution URL. Present on listings too, for the device preview. */
  url: string
  /** Playlist names using this media. Populated on detail, empty in listings. */
  used_in: string[]
  /** A video's normalised playback copy (H.264, up to 4K, 30 fps): false while it is still being
   *  made, true once screens can have it — or once it failed, with `playback_error` saying why,
   *  in which case screens play the original. Always true for images. */
  playback_ready: boolean
  /** Whether the file was re-encoded, or only remuxed because it already met the target. */
  playback_reencoded: boolean
  playback_error: string | null
}

export type MediaDetail = MediaRead

export interface UploadTicket {
  media_id: string
  upload_url: string
  thumbnail_upload_url: string
}

export interface CompleteBody {
  checksum: string
  width?: number | null
  height?: number | null
  duration_seconds?: number | null
}

// --- Playlists ---

export type ItemFit = 'contain' | 'cover' | 'stretch'

export interface ItemMedia {
  id: string
  filename: string
  kind: MediaKind
  thumbnail_url: string | null
  /** Presigned full-resolution URL, for the device preview. */
  url: string
  width: number | null
  height: number | null
  duration_seconds: number | null
}

export interface ElementRead {
  id: string
  /** Paint order within the scene — higher draws on top. */
  z_index: number
  /** Normalized [0,1] against the scene's own frame, deliberately unclamped — an element can
   *  sit partially off-canvas, same as any real design surface. */
  x: number
  y: number
  width: number
  height: number
  fit: ItemFit
  /** Normalized [0,1] crop center + zoom (>=1), relative to this element's own box. Stored
   *  regardless of `fit`, only rendered when fit === 'cover'. See src/utils/cropMath.ts for
   *  how these resolve into a rectangle. */
  crop_x: number | null
  crop_y: number | null
  crop_zoom: number | null
  /** Video only. Every video is muted unless this is set. */
  has_audio: boolean
  /** Video only. Degrees clockwise (0/90/180/270) to correct a file shot sideways. */
  rotation_degrees: number
  /** A file element's media — null for a website element, which has `web_url` instead. */
  media: ItemMedia | null
  web_url: string | null
}

/** What shows wherever a scene's elements don't cover the screen. See utils/sceneBackground.ts. */
export type SceneBackground = 'black' | 'blur'

export interface PlaylistItemRead {
  id: string
  position: number
  duration_seconds: number
  is_enabled: boolean
  background: SceneBackground
  elements: ElementRead[]
}

export interface PlaylistSummary {
  id: string
  name: string
  shuffle: boolean
  item_count: number
  total_duration_seconds: number
  created_at: string
  updated_at: string
  /** A preview strip, not the whole loop — capped server-side. `null` for a scene whose
   *  media has no thumbnail: a blank tile, not a skipped one. */
  thumbnails: (string | null)[]
}

export interface PlaylistDetail extends PlaylistSummary {
  items: PlaylistItemRead[]
  /** Device names this playlist is assigned to. */
  used_by: string[]
}

export interface ElementWrite {
  /** Exactly one of these: a library file, or a website (https). */
  media_id?: string | null
  web_url?: string | null
  z_index?: number
  x?: number
  y?: number
  width?: number
  height?: number
  fit?: ItemFit
  crop_x?: number | null
  crop_y?: number | null
  crop_zoom?: number | null
  has_audio?: boolean
  rotation_degrees?: number
}

export interface ItemWrite {
  duration_seconds?: number | null
  is_enabled?: boolean
  background?: SceneBackground
  elements: ElementWrite[]
}

// --- Devices ---

/** Rotation of the content, clockwise from the panel's own landscape — see utils/orientation.ts. */
export type DeviceOrientation = '0' | '90' | '180' | '270'

/** Which player the screen runs. A web screen updates by reloading the deployed web player,
 *  so software rollouts (APKs) never apply to it. */
export type DevicePlatform = 'android' | 'web'

export interface DeviceRead {
  id: string
  name: string
  location: string
  /** IANA name. Schedules are expressed in this screen's local wall clock. */
  timezone: string
  orientation: DeviceOrientation
  platform: DevicePlatform
  playlist_id: string | null
  screen_width: number | null
  screen_height: number | null
  app_version: string | null
  last_seen_at: string | null
  paired_at: string | null
  /** A single-device update pinned independent of the fleet rollout — null means nothing is
   *  pending. Cleared automatically once the screen reports running it. Owner-only to set. */
  forced_update_version: string | null
  /** When that pinned update takes effect — null means on the screen's next check-in. */
  forced_update_at: string | null
  /** What the screen itself last said about installing a build — null until a screen running
   *  a player new enough to report has been offered one. Read alongside `forced_update_version`
   *  (see utils/updateStatus.ts): a pin with no report yet is "pending"; a report can also be
   *  about a fleet rollout, with no pin at all. `installed` is set by the server the moment the
   *  screen heartbeats with the target version — a screen can't report its own success. */
  update_state: DeviceUpdateState | null
  update_version: string | null
  update_progress_pct: number | null
  /** The reason, in the screen's own words, when `update_state` is 'failed'. */
  update_detail: string | null
  update_reported_at: string | null
  /** Playback health from the last heartbeat: frames the decoder dropped since the beat before,
   *  the hardware decoder in use, and the last measured media download speed. Null on players
   *  that predate reporting. */
  playback_dropped_frames: number | null
  playback_decoder: string | null
  download_bytes_per_second: number | null
  playback_reported_at: string | null
}

export type DeviceUpdateState = 'downloading' | 'installing' | 'installed' | 'failed'

export interface ClaimBody {
  pairing_code: string
  name: string
  location?: string
}

export interface DeviceUpdateBody {
  name?: string
  location?: string
  timezone?: string
  orientation?: DeviceOrientation
  playlist_id?: string | null
  /** Explicit, because `playlist_id: null` is indistinguishable from "not sent". */
  clear_playlist?: boolean
}

export interface DeviceUpdateVersionBody {
  version: string
  /** Omit (or null) to install on the next check-in; a future instant holds it until then. */
  scheduled_at?: string | null
}

/** What a device is playing right now — the read-only counterpart to Campaign. */
export interface DeviceResolutionRead {
  device_id: string
  playlist_id: string | null
  schedule_id: string | null
  schedule_name: string | null
  campaign_id: string | null
  valid_until: string | null
  timezone: string
  device_local_time: string
}

/** Baseline to watch after asking a screen to check in — see useDeviceDetail.ts's probe(). */
export interface ProbeResponse {
  probed_at: string
  previous_last_seen_at: string | null
}

// --- Device settings ---
// Remotely-configurable values pushed to the screen — volume today, and by the same
// mechanism, brightness/power scheduling/app lock/touchscreen lock later. `value` is
// deliberately untyped here: each key's shape is whatever DeviceSettingsContainer.vue's
// SETTINGS registry says it is, validated server-side, not by this interface.

export interface DeviceSettingRead {
  key: string
  value: unknown
  updated_at: string
  /** What the device's own heartbeat most recently said this actually is, and when — both
   *  null until the first heartbeat that reports this key. Independent of `value`: a change
   *  still in flight, or someone adjusting the screen by hand, can disagree with it. */
  reported_value: unknown
  reported_at: string | null
}

/** A screen's power, resolved from its schedule and any manual override — see backend
 *  services/power.py. */
export interface PowerStatusRead {
  state: 'on' | 'off'
  /** override: a manual "turn on/off now"; schedule: the weekly window; default: neither. */
  source: 'override' | 'schedule' | 'default'
  /** When `state` ends on its own, ISO-8601 in the device's timezone (with offset). */
  until: string | null
  schedule_enabled: boolean
  timezone: string
  device_local_time: string
  /** What the screen itself last reported — null before a player that reports power has
   *  heartbeated. */
  reported_state: 'on' | 'off' | null
  reported_at: string | null
}

// --- Users (owner only) ---

export interface AccountUserRead {
  id: string
  username: string
  email: string | null
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  device_count: number
  device_ids: string[]
}

export interface ManagerCreateBody {
  username: string
  password: string
  display_name: string
  email?: string | null
  device_ids?: string[]
}

// --- Schedules (dayparting) ---

/** Bit 0 = Monday … bit 6 = Sunday, matching the backend's mask and Python's weekday(). */
export const DAY_BITS = [
  { bit: 1 << 0, short: 'Mon' },
  { bit: 1 << 1, short: 'Tue' },
  { bit: 1 << 2, short: 'Wed' },
  { bit: 1 << 3, short: 'Thu' },
  { bit: 1 << 4, short: 'Fri' },
  { bit: 1 << 5, short: 'Sat' },
  { bit: 1 << 6, short: 'Sun' },
] as const

export const ALL_DAYS = 0b1111111
export const WEEKDAYS = 0b0011111
export const WEEKENDS = 0b1100000

/** What a device is playing right now, and why. */
export interface ResolutionRead {
  playlist_id: string | null
  schedule_id: string | null
  schedule_name: string | null
  campaign_id: string | null
  valid_until: string | null
  timezone: string
  device_local_time: string
}

// --- Campaigns ---
// A campaign is a named set of devices plus the playlist-on-schedule rules that play across
// all of them. It owns the `Schedule` rows it produces — one per (device, rule) pair — so
// editing one regenerates that whole set rather than patching individual schedules.

export interface CampaignRuleWrite {
  playlist_id: string
  name?: string
  days_of_week?: number
  starts_at: string
  ends_at: string
  priority?: number
  /** Both inclusive, both optional and independent — null/omitted means unbounded on that
   *  side, so an ordinary rule with no date range needs neither. */
  start_date?: string | null
  end_date?: string | null
  /** `HH:MM:SS`, device-local, narrowing the first/last day. Each requires its date. */
  start_time?: string | null
  end_time?: string | null
}

export interface CampaignRuleRead {
  playlist_id: string
  name: string
  days_of_week: number
  starts_at: string
  ends_at: string
  priority: number
  start_date: string | null
  end_date: string | null
  start_time: string | null
  end_time: string | null
}

export interface CampaignWrite {
  name: string
  device_ids: string[]
  rules: CampaignRuleWrite[]
}

export interface CampaignSummary {
  id: string
  name: string
  device_ids: string[]
  device_count: number
  rule_count: number
  /** Distinct playlists across the rules. */
  playlist_count: number
  created_at: string
  updated_at: string
}

export interface CampaignRead {
  id: string
  name: string
  device_ids: string[]
  rules: CampaignRuleRead[]
  created_at: string
  updated_at: string
}

export interface CampaignSaveResult {
  campaign: CampaignRead
  /** Requested device ids the caller couldn't reach — dropped rather than failing the save. */
  skipped_device_ids: string[]
}

// --- Operations ---

export interface StorageRead {
  used_bytes: number
  /** null means unlimited. */
  quota_bytes: number | null
  file_count: number
}

export interface DeviceHealthRead {
  device_id: string
  name: string
  last_seen_at: string | null
  minutes_since_seen: number | null
  is_online: boolean
  error_count_24h: number
  plays_24h: number
  app_version: string | null
}

export interface DeviceEventRead {
  id: string
  level: 'info' | 'error'
  message: string
  created_at: string
}

export interface PlayEventRead {
  id: string
  media_id: string | null
  filename: string
  started_at: string
  seconds: number
}

// --- Player rollouts (owner only) ---
// Which player-app build every screen should be running, and when it took (or will take)
// effect. Replaces manually flipping env vars after `publish_player_apk.py` — a rollout can
// now be scheduled for later, not just applied immediately.

export interface PlayerReleaseRead {
  version: string
  size_bytes: number
  uploaded_at: string
  is_current: boolean
}

export interface PlayerRolloutWrite {
  version: string
  /** Omit (or null) to publish immediately. */
  scheduled_at?: string | null
}

export interface PlayerRolloutRead {
  id: string
  version: string
  scheduled_at: string
  created_at: string
  is_active: boolean
}
