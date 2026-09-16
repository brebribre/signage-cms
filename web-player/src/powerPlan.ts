import type { PowerOverride, PowerSchedule } from './api'

/**
 * Whether the screen should be on right now: its weekly power schedule plus a temporary manual
 * override. A port of the Android player's `power/PowerPlan.kt` — the same three rules, the same
 * answers, pinned by the same cases in test/powerPlan.test.ts. The CMS keeps a third copy
 * (`backend/app/services/power.py`); all three must stay in step.
 *
 * 1. An override that hasn't ended wins. An override with no end only counts while there is no
 *    schedule.
 * 2. Otherwise an enabled schedule decides: on inside the day's window, off outside it, and off
 *    all day on days that aren't selected. A window ending before it starts runs through
 *    midnight and belongs to the day it starts on.
 * 3. Otherwise the screen is on — but only once power has been configured at all.
 *
 * Pure: no DOM and no clock of its own. Time zones go through `Intl`, which every browser this
 * runs on already carries a tz database for — no library needed.
 */

export type PowerSource = 'override' | 'schedule' | 'default'

export interface PowerDecision {
  on: boolean
  source: PowerSource
  /** When this answer stops being true on its own, if ever. */
  nextChangeMillis: number | null
}

/** A week covers every pattern; the extra day covers a window crossing midnight. */
const LOOKAHEAD_DAYS = 8
const DAY_MS = 86_400_000

interface LocalDateTime {
  year: number
  month: number
  day: number
  /** Milliseconds since local midnight. */
  timeMs: number
  /** Monday = 0, matching the bitmask. */
  weekday: number
}

const formatters = new Map<string, Intl.DateTimeFormat>()

function formatterFor(zone: string): Intl.DateTimeFormat {
  let f = formatters.get(zone)
  if (!f) {
    f = new Intl.DateTimeFormat('en-US', {
      timeZone: zone,
      hourCycle: 'h23',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
    })
    formatters.set(zone, f)
  }
  return f
}

/** The zone to evaluate in: the CMS's, if this browser knows it, else the screen's own. */
export function resolveZone(zone: string | null | undefined): string {
  if (zone) {
    try {
      formatterFor(zone)
      return zone
    } catch {
      /* an unknown name falls through, the same as ZoneId.of failing on Android */
    }
  }
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
}

function localAt(millis: number, zone: string): LocalDateTime {
  const parts: Record<string, number> = {}
  for (const p of formatterFor(zone).formatToParts(new Date(millis))) {
    if (p.type !== 'literal') parts[p.type] = Number(p.value)
  }
  // Some engines render midnight as hour 24 even with h23.
  const hour = parts.hour % 24
  const ms = ((millis % 1000) + 1000) % 1000
  return {
    year: parts.year,
    month: parts.month,
    day: parts.day,
    timeMs: ((hour * 60 + parts.minute) * 60 + parts.second) * 1000 + ms,
    weekday: (new Date(Date.UTC(parts.year, parts.month - 1, parts.day)).getUTCDay() + 6) % 7,
  }
}

/** The instant a local wall-clock moment falls on in [zone] — `ZonedDateTime.of(...).toInstant()`. */
function instantOf(year: number, month: number, day: number, timeMs: number, zone: string): number {
  const wall = Date.UTC(year, month - 1, day) + timeMs
  const offsetAt = (t: number) => {
    const l = localAt(t, zone)
    return Date.UTC(l.year, l.month - 1, l.day) + l.timeMs - t
  }
  // Two passes settle a guess that landed on the other side of a DST change.
  let guess = wall - offsetAt(wall)
  guess = wall - offsetAt(guess)
  return guess
}

function parseTime(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return (h * 60 + m) * 60_000
}

function days(schedule: PowerSchedule): number {
  return schedule.days_of_week ?? 0b1111111
}

export function scheduledOn(schedule: PowerSchedule, local: LocalDateTime): boolean {
  const on = parseTime(schedule.power_on ?? '08:00')
  const off = parseTime(schedule.power_off ?? '22:00')
  const t = local.timeMs
  const selected = (day: number) => (days(schedule) & (1 << ((day + 7) % 7))) !== 0

  if (on < off) return selected(local.weekday) && t >= on && t < off
  // Crosses midnight: late on a selected day, or early the morning after one.
  if (t >= on) return selected(local.weekday)
  if (t < off) return selected(local.weekday - 1)
  return false
}

/** The next moment the schedule's answer actually flips, skipping edges that change nothing. */
export function nextChangeMillis(schedule: PowerSchedule, nowMillis: number, zone: string): number | null {
  const local = localAt(nowMillis, zone)
  const current = scheduledOn(schedule, local)
  const edges = [parseTime(schedule.power_on ?? '08:00'), parseTime(schedule.power_off ?? '22:00')]
  const midnight = Date.UTC(local.year, local.month - 1, local.day)

  const candidates: number[] = []
  for (let offset = 0; offset < LOOKAHEAD_DAYS; offset++) {
    const date = new Date(midnight + offset * DAY_MS)
    for (const edge of edges) {
      candidates.push(instantOf(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate(), edge, zone))
    }
  }
  candidates.sort((a, b) => a - b)
  for (const at of candidates) {
    if (at > nowMillis && scheduledOn(schedule, localAt(at, zone)) !== current) return at
  }
  return null
}

export function parseInstantMillis(iso: string | null | undefined): number | null {
  if (!iso) return null
  const t = Date.parse(iso)
  return Number.isNaN(t) ? null : t
}

export function decide(
  schedule: PowerSchedule | null | undefined,
  override: PowerOverride | null | undefined,
  nowMillis: number,
  zone: string,
): PowerDecision | null {
  const hasSchedule = schedule?.enabled === true

  if (override && (override.state === 'on' || override.state === 'off')) {
    const on = override.state === 'on'
    if (override.until == null) {
      if (!hasSchedule) return { on, source: 'override', nextChangeMillis: null }
    } else {
      const until = parseInstantMillis(override.until)
      if (until !== null && nowMillis < until) return { on, source: 'override', nextChangeMillis: until }
    }
  }

  if (hasSchedule) {
    return {
      on: scheduledOn(schedule!, localAt(nowMillis, zone)),
      source: 'schedule',
      nextChangeMillis: nextChangeMillis(schedule!, nowMillis, zone),
    }
  }

  // An override existed but has ended, and there is no schedule to fall back on.
  return override ? { on: true, source: 'default', nextChangeMillis: null } : null
}
