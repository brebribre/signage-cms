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
}

// --- Devices ---

export type DeviceOrientation = 'landscape' | 'portrait'

export interface DeviceRead {
  id: string
  name: string
  location: string
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
