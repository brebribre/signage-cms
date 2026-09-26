/** Response types mirroring the backend's Pydantic models — only what /admin/* speaks. */

export type UserRole = 'owner' | 'manager'

/** What sort of account this is — which decides who may use this app and what they may do.
 *  - `owner`: Paskall itself. One only, no limits. Issues admin and client accounts.
 *  - `admin`: a technician. Uses this app too, but issues client accounts only.
 *  - `client`: a customer. The CMS only, never this app. */
export type AccountKind = 'owner' | 'admin' | 'client'

/** Who is signed in here. Always staff — /admin/me refuses everyone else — and `kind` is
 *  their account's kind, which is what decides what this app offers them. */
export interface StaffRead {
  id: string
  username: string
  display_name: string
  kind: AccountKind
}

export interface LoginBody {
  identifier: string
  password: string
}

/** One person who can sign in to an account: its main user (owner), or a sub account
 *  (manager) they created. */
export interface AdminAccountUserRead {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  /** Still on a password staff (or their main user) chose; they haven't signed in to pick
   *  their own yet. */
  must_change_password?: boolean
}

/** One account: its kind, its limits and how much of each is used. A null limit means
 *  unlimited. */
export interface AdminAccountRead {
  id: string
  name: string
  kind: AccountKind
  created_at: string
  /** The first owner's username — what staff tell the customer to sign in with. */
  owner_username: string | null
  /** Everyone in the account, owners first, so sub accounts sit under the owner. */
  users: AdminAccountUserRead[]
  max_screens: number | null
  screens_used: number
  storage_quota_bytes: number | null
  storage_used_bytes: number
  /** The moment the account stops accepting changes; null means never. After it, the CMS is
   *  read-only for everyone in the account, and an admin account loses this app. */
  expires_at: string | null
  /** Worked out by the server, so a wrong clock here cannot mislabel an account. */
  is_expired: boolean
}

export interface AdminAccountCreateBody {
  name: string
  kind: AccountKind
  username: string
  password: string
  display_name: string
  email?: string | null
  max_screens: number | null
  storage_quota_bytes: number | null
  expires_at?: string | null
}

/** Only the fields sent change. A field sent as null becomes unlimited, or has no end date. */
export interface AdminLimitsUpdateBody {
  max_screens?: number | null
  storage_quota_bytes?: number | null
  /** null = no end date. A moment already past makes the account read-only at once. */
  expires_at?: string | null
}

/** One part of the R2 bucket, told apart by its key. `objects` is null when the bucket could
 *  not be read and the figure came from the database instead. */
export interface StoragePart {
  key: 'media' | 'copies' | 'thumbnails' | 'builds' | 'other'
  label: string
  bytes: number
  objects: number | null
}

/** The platform in numbers — GET /admin/infrastructure. */
export interface InfrastructureRead {
  storage: {
    /** Our own upgrade line (the backend's R2_STORAGE_LIMIT_GB), not a ceiling R2 enforces. */
    limit_bytes: number
    used_bytes: number
    /** `bucket`: R2 itself was measured. `database`: it could not be, so this is what the
     *  media table knows about — no thumbnails, builds or orphans. */
    source: 'bucket' | 'database'
    object_count: number | null
    measured_at: string
    parts: StoragePart[]
    /** Media (with its copies) added in the last 30 days and still here. */
    added_30d_bytes: number
    /** Oldest month first; "2026-09". */
    monthly: { month: string; bytes: number }[]
    top_accounts: { id: string; name: string; bytes: number }[]
    bucket_error: string | null
  }
  users: {
    total: number
    active: number
    main_users: number
    sub_accounts: number
    new_30d: number
    accounts: number
    client_accounts: number
  }
  screens: {
    paired: number
    online: number
    android: number
    web: number
    new_30d: number
  }
  generated_at: string
}
