import { useExpiry } from '@/hooks/useExpiry'
import type { AccountKind, AdminAccountRead, AdminAccountUserRead } from '@/types/api'

export const BADGE =
  'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] leading-4 whitespace-nowrap ring-1 ring-inset'
export const TONES = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  brand: 'bg-brand-soft text-brand ring-brand/20',
  muted: 'bg-surface text-ink-muted ring-line',
  ink: 'bg-ink text-ink-inverse ring-ink',
  danger: 'bg-red-50 text-danger ring-red-200',
  amber: 'bg-amber-50 text-amber-700 ring-amber-200',
} as const
export type Tone = keyof typeof TONES
export interface Mark {
  label: string
  tone: Tone
}

/** Only the accounts that are *not* ordinary customers carry a kind badge. A mark on every row
 *  marks nothing; a mark on the two that can sign in here is worth reading. This is the only
 *  badge allowed to say "Owner", and it means the account kind — Marien itself. */
export const KIND_TONE: Partial<Record<AccountKind, Tone>> = { owner: 'ink', admin: 'brand' }

/** The person the account was issued to. */
export function mainUser(a: AdminAccountRead): AdminAccountUserRead | null {
  return a.users.find((u) => u.role === 'owner') ?? null
}

/** Everyone else in the account, in the order the server sent them: sub accounts, and any
 *  second owner an account picked up along the way. */
export function otherUsers(a: AdminAccountRead): AdminAccountUserRead[] {
  const main = mainUser(a)
  return a.users.filter((u) => u.id !== main?.id)
}

/** "BR" for "Bryan Alvin", "K" for "Kopi" — the letters on an account's or person's avatar. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return ((words[0]?.[0] ?? '?') + (words.length > 1 ? words[words.length - 1]![0] : '')).toUpperCase()
}

/** The marks shared by the Accounts table and an account's side panel, so the two never
 *  describe the same account differently. */
export function useAccountMarks() {
  const { daysLeft, endsSoon } = useExpiry()

  /** An account past its end date, or close to it. Staff are the ones who renew, so both are
   *  marked: one to act on now, one to see coming. */
  function endBadge(a: AdminAccountRead): Mark | null {
    if (a.is_expired) return { label: 'Expired', tone: 'danger' }
    if (a.expires_at && endsSoon(a.expires_at, a.is_expired)) {
      const n = daysLeft(a.expires_at)
      return { label: n <= 1 ? 'Ends today' : `Ends in ${n} days`, tone: 'amber' }
    }
    return null
  }

  function userBadges(u: AdminAccountUserRead): Mark[] {
    const out: Mark[] = [
      u.role === 'owner' ? { label: 'Main user', tone: 'green' } : { label: 'Sub account', tone: 'brand' },
    ]
    if (!u.is_active) out.push({ label: 'Deactivated', tone: 'muted' })
    if (u.must_change_password) out.push({ label: 'Temporary password', tone: 'muted' })
    return out
  }

  return { endBadge, userBadges }
}
