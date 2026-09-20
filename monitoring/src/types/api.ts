/** Response types mirroring the backend's Pydantic models — only what /admin/* speaks. */

export type UserRole = 'owner' | 'manager'

/** Who is signed in here. Always a platform admin — /admin/me refuses anyone else. */
export interface UserRead {
  id: string
  username: string
  email: string | null
  display_name: string
  role: UserRole
  is_active: boolean
  is_platform_admin: boolean
  created_at: string
}

export interface LoginBody {
  identifier: string
  password: string
}

/** One person who can sign in to a customer account: the owner, or a sub account (manager)
 *  the owner created. */
export interface AdminAccountUserRead {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

/** One customer account: its limits and how much of each is used. A null limit means
 *  unlimited. */
export interface AdminAccountRead {
  id: string
  name: string
  created_at: string
  /** The first owner's username — what the admin tells the customer to sign in with. */
  owner_username: string | null
  /** Everyone in the account, owners first, so sub accounts sit under the owner. */
  users: AdminAccountUserRead[]
  max_screens: number | null
  screens_used: number
  storage_quota_bytes: number | null
  storage_used_bytes: number
}

export interface AdminAccountCreateBody {
  name: string
  username: string
  password: string
  display_name: string
  email?: string | null
  max_screens: number | null
  storage_quota_bytes: number | null
}

/** Only the fields sent change. A field sent as null becomes unlimited. */
export interface AdminLimitsUpdateBody {
  max_screens?: number | null
  storage_quota_bytes?: number | null
}
