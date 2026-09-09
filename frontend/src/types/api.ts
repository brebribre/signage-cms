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

export interface PlaylistItemRead {
  id: string
  position: number
  duration_seconds: number
  fit: ItemFit
  is_enabled: boolean
  /** Normalized [0,1] crop center + zoom (>=1). Stored regardless of `fit`, only rendered
   *  when fit === 'cover'. See src/utils/cropMath.ts for how these resolve into a rectangle. */
  crop_x: number | null
  crop_y: number | null
  crop_zoom: number | null
  /** Video only. trim_end_seconds null means "to the end". */
  trim_start_seconds: number
  trim_end_seconds: number | null
  media: ItemMedia
}

export interface PlaylistSummary {
  id: string
  name: string
  shuffle: boolean
  item_count: number
  total_duration_seconds: number
  created_at: string
  updated_at: string
}

export interface PlaylistDetail extends PlaylistSummary {
  items: PlaylistItemRead[]
  /** Device names this playlist is assigned to. */
  used_by: string[]
}

export interface ItemWrite {
  media_id: string
  duration_seconds?: number | null
  fit?: ItemFit
  is_enabled?: boolean
  crop_x?: number | null
  crop_y?: number | null
  crop_zoom?: number | null
  trim_start_seconds?: number
  trim_end_seconds?: number | null
}

// --- Devices ---

export type DeviceOrientation = 'landscape' | 'portrait'

export interface DeviceRead {
  id: string
  name: string
  location: string
  /** IANA name. Schedules are expressed in this screen's local wall clock. */
  timezone: string
  orientation: DeviceOrientation
  playlist_id: string | null
  screen_width: number | null
  screen_height: number | null
  app_version: string | null
  last_seen_at: string | null
  paired_at: string | null
}

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

/** Returned by unpair — the screen's new pairing code, same shape as a fresh boot. */
export interface PairStartResponse {
  device_id: string
  pairing_code: string
  poll_token: string
  expires_at: string
  poll_seconds: number
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

export interface ScheduleRead {
  id: string
  device_id: string
  playlist_id: string
  name: string
  days_of_week: number
  /** "HH:MM:SS" local to the device. */
  starts_at: string
  ends_at: string
  priority: number
  is_enabled: boolean
  created_at: string
}

export interface ScheduleWrite {
  playlist_id: string
  name?: string
  days_of_week?: number
  starts_at: string
  ends_at: string
  priority?: number
}

export interface ScheduleUpdateBody extends Partial<ScheduleWrite> {
  is_enabled?: boolean
}

/** What a device is playing right now, and why. */
export interface ResolutionRead {
  playlist_id: string | null
  schedule_id: string | null
  schedule_name: string | null
  valid_until: string | null
  timezone: string
  device_local_time: string
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
