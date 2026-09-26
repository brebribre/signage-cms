/**
 * Week-relative interval math for daily time windows, used to catch overlapping slots before
 * they're saved. Mirrors `services/scheduling._covers` on the backend: a window whose end is
 * at or before its start runs through midnight and belongs to the day it starts on.
 */

export const DAY_MINUTES = 24 * 60
export const WEEK_MINUTES = DAY_MINUTES * 7

export interface TimeWindow {
  /** `HH:MM`, the screen's local wall clock. */
  starts_at: string
  ends_at: string
  /** Bit 0 = Monday … bit 6 = Sunday. */
  days_of_week: number
}

/** The colours WeekTimeline draws slots in, by `TimelineSlot.tone` — exported so a list beside
 *  the timeline can mark each entry with the same swatch. The brand blues, all readable against
 *  the light grey "asleep" ground. */
export const TIMELINE_TONES = ['#003399', '#0076dd', '#1f55c4', '#7fa1e6'] as const
export const timelineTone = (tone: number) => TIMELINE_TONES[tone % TIMELINE_TONES.length]

/** A window as `WeekTimeline.vue` draws it. */
export interface TimelineSlot extends TimeWindow {
  key: string
  label: string
  /** Index into the tone ramp — callers give the same playlist the same tone. */
  tone: number
  invalid?: boolean
}

export function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}

/** How many minutes the window runs for — 0 when start equals end, which the backend rejects. */
export function windowLength(w: TimeWindow): number {
  const start = toMinutes(w.starts_at)
  const end = toMinutes(w.ends_at)
  if (start === end) return 0
  return end > start ? end - start : end + DAY_MINUTES - start
}

export function crossesMidnight(w: TimeWindow): boolean {
  return toMinutes(w.ends_at) < toMinutes(w.starts_at)
}

/** `[start, end)` in minutes from Monday 00:00, one per selected day — split in two where a
 *  Sunday-night window wraps into Monday morning, so every interval stays inside the week. */
export function weekIntervals(w: TimeWindow): [number, number][] {
  const length = windowLength(w)
  if (!length) return []
  const out: [number, number][] = []
  for (let day = 0; day < 7; day++) {
    if (!(w.days_of_week & (1 << day))) continue
    const start = day * DAY_MINUTES + toMinutes(w.starts_at)
    const end = start + length
    if (end <= WEEK_MINUTES) {
      out.push([start, end])
    } else {
      out.push([start, WEEK_MINUTES])
      out.push([0, end - WEEK_MINUTES])
    }
  }
  return out
}

export function windowsOverlap(a: TimeWindow, b: TimeWindow): boolean {
  const others = weekIntervals(b)
  return weekIntervals(a).some(([s1, e1]) => others.some(([s2, e2]) => s1 < e2 && s2 < e1))
}

/** The part of a window that falls on one day, as `[start, end)` minutes within that day. */
export function segmentsOnDay(w: TimeWindow, day: number): [number, number][] {
  const dayStart = day * DAY_MINUTES
  const dayEnd = dayStart + DAY_MINUTES
  return weekIntervals(w)
    .map(([s, e]): [number, number] => [Math.max(s, dayStart) - dayStart, Math.min(e, dayEnd) - dayStart])
    .filter(([s, e]) => e > s)
}
