import { useFormat } from '@/hooks/useFormat'

/**
 * An account's end date, as people think of it and as the server stores it.
 *
 * People pick a day: "active until 30 Sep". The server stores a moment: the account stops the
 * instant `expires_at` passes. The two meet at midnight, local time, at the *end* of the day
 * picked — so "active until 30 Sep" works all of 30 Sep and stops as 1 Oct begins. Reading it
 * back, a millisecond before that moment is still 30 Sep, which gives the same day again.
 *
 * Local time is the browser's. Staff and customers are in the same country, so the day a
 * technician picks is the day the customer sees.
 */

/** How close is "soon"? Accounts inside this many days get marked, so staff can follow up. */
export const ENDS_SOON_DAYS = 14

const DAY_MS = 24 * 60 * 60 * 1000

function lastDay(iso: string): Date {
  return new Date(new Date(iso).getTime() - 1)
}

export function useExpiry() {
  const { date } = useFormat()

  /** A date field's "YYYY-MM-DD" → the moment the account stops. Blank means no end date. */
  function toExpiresAt(day: string): string | null {
    if (!day) return null
    const [y, m, d] = day.split('-').map(Number)
    return new Date(y, m - 1, d + 1).toISOString()
  }

  /** The moment the account stops → the "YYYY-MM-DD" a date field shows: its last working day. */
  function toDayField(iso: string | null): string {
    if (!iso) return ''
    const d = lastDay(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  }

  /** "30 Sep 2026": the last day the account works. */
  function lastDayText(iso: string): string {
    return date(lastDay(iso).toISOString())
  }

  /** Whole days left before it stops, rounded up — 0 once it has. */
  function daysLeft(iso: string): number {
    return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / DAY_MS))
  }

  function endsSoon(iso: string | null, isExpired: boolean): boolean {
    return !!iso && !isExpired && daysLeft(iso) <= ENDS_SOON_DAYS
  }

  return { toExpiresAt, toDayField, lastDayText, daysLeft, endsSoon }
}
