import { computed } from 'vue'

import { useAuth } from '@/hooks/useAuth'
import type { AccountKind, AdminAccountRead } from '@/types/api'

/**
 * What the signed-in member of staff may do — a mirror of the server's rules, used only to
 * decide what this app offers. The server checks the same things again on every call and
 * answers 403, so nothing here is a control; hiding a button the server would refuse is a
 * courtesy, not a lock.
 *
 * The table, the same one as services/admin.py::MAY_ISSUE:
 *
 *   owner  → issues admin and client accounts, and sets the limits of both
 *   admin  → issues client accounts, and sets client limits only
 *
 * Nobody issues a second owner account, and nobody sets limits on the one there is.
 */
const MAY_ISSUE: Record<string, AccountKind[]> = {
  owner: ['admin', 'client'],
  admin: ['client'],
}

const LABELS: Record<AccountKind, string> = {
  owner: 'Owner',
  admin: 'Admin',
  client: 'Client',
}

/** What a new account of each kind starts with when nobody types a number. Matches
 *  services/admin.py::default_limits — an admin gets the standard allowance, a client is
 *  unlimited until staff say otherwise. */
const DEFAULT_LIMITS: Record<AccountKind, { screens: string; storageGb: string }> = {
  owner: { screens: '', storageGb: '' },
  admin: { screens: '15', storageGb: '5' },
  client: { screens: '', storageGb: '' },
}

export function useStaffRights() {
  const { kind } = useAuth()

  /** The kinds this person may issue, in the order the dropdown should offer them. */
  const issuable = computed<AccountKind[]>(() => (kind.value ? MAY_ISSUE[kind.value] ?? [] : []))

  /** Whether this person may change that account's limits. Same rule as issuing. */
  function maySetLimits(account: AdminAccountRead): boolean {
    return account.kind !== 'owner' && issuable.value.includes(account.kind)
  }

  function label(k: AccountKind): string {
    return LABELS[k]
  }

  function defaultLimits(k: AccountKind) {
    return { ...DEFAULT_LIMITS[k] }
  }

  return { kind, issuable, maySetLimits, label, defaultLimits }
}
