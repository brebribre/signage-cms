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
