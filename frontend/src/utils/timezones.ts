/**
 * The timezones offered in a picker: the ones this fleet is likely to be in first, then any the
 * current value or this browser needs that aren't among them — so a saved zone is always shown,
 * and "where I am" is always one pick away.
 */
export const COMMON_ZONES = [
  'UTC',
  'Asia/Jakarta',
  'Asia/Singapore',
  'Asia/Kuala_Lumpur',
  'Asia/Bangkok',
  'Asia/Tokyo',
  'Australia/Sydney',
  'Europe/London',
  'Europe/Amsterdam',
  'America/New_York',
  'America/Los_Angeles',
]

/** This browser's own zone, or null where it can't say. */
export function browserZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

export function zoneOptions(...include: (string | null | undefined)[]): string[] {
  const extra = include.filter((z): z is string => !!z && !COMMON_ZONES.includes(z))
  return [...new Set([...extra, ...COMMON_ZONES])]
}
