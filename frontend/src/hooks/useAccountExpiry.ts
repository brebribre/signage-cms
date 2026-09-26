import { computed } from 'vue'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'

/** Warn this many days ahead, so there is time to renew before anything stops. */
const WARN_DAYS = 14
const DAY_MS = 24 * 60 * 60 * 1000

/**
 * The account's end date, as the CMS tells people about it.
 *
 * Marien sets it from the monitoring app. The server stores the moment the account stops,
 * which is midnight at the end of the last working day, so the day to show is a millisecond
 * before it. After that moment the server refuses every change; this only explains why.
 */
export function useAccountExpiry() {
  const { account } = useAuth()
  const { date } = useFormat()

  const expiresAt = computed(() => account.value?.expires_at ?? null)
  const isExpired = computed(() => account.value?.is_expired ?? false)

  /** "30 Sep 2026": the last day the account works. */
  const lastDay = computed(() =>
    expiresAt.value ? date(new Date(new Date(expiresAt.value).getTime() - 1).toISOString()) : null,
  )

  const daysLeft = computed(() =>
    expiresAt.value ? Math.max(0, Math.ceil((new Date(expiresAt.value).getTime() - Date.now()) / DAY_MS)) : null,
  )

  const endsSoon = computed(() => !isExpired.value && daysLeft.value !== null && daysLeft.value <= WARN_DAYS)

  return { expiresAt, isExpired, lastDay, daysLeft, endsSoon }
}
