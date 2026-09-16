/**
 * The power rules, pinned — case for case the same as the Android player's PowerPlanTest.kt and
 * backend/scripts/check_power.py. The CMS shows what these decide, so all three must agree.
 *
 * 2026-09-07 is a Monday.
 */
import { describe, expect, it } from 'vitest'

import { decide } from '../src/powerPlan'

const JAKARTA = 'Asia/Jakarta' // UTC+7, no DST
const at = (day: number, hour: number, minute = 0) => Date.UTC(2026, 8, day, hour - 7, minute)
const iso = (millis: number) => new Date(millis).toISOString()

const weekdays = { enabled: true, days_of_week: 0b0011111, power_on: '08:00', power_off: '22:00' }
const nightly = { enabled: true, days_of_week: 0b1111111, power_on: '20:00', power_off: '02:00' }

describe('schedule', () => {
  it('inside the window is on, and the next change is the off time', () => {
    const d = decide(weekdays, null, at(7, 10), JAKARTA)!
    expect(d.on).toBe(true)
    expect(d.source).toBe('schedule')
    expect(d.nextChangeMillis).toBe(at(7, 22))
  })

  it('after the off time is off until the next morning', () => {
    const d = decide(weekdays, null, at(7, 23), JAKARTA)!
    expect(d.on).toBe(false)
    expect(d.nextChangeMillis).toBe(at(8, 8))
  })

  it('the start is inclusive and the end exclusive', () => {
    expect(decide(weekdays, null, at(7, 8), JAKARTA)!.on).toBe(true)
    expect(decide(weekdays, null, at(7, 22), JAKARTA)!.on).toBe(false)
  })

  it('an unselected day is off all day, until the next selected morning', () => {
    const d = decide(weekdays, null, at(12, 10), JAKARTA)!
    expect(d.on).toBe(false)
    expect(d.nextChangeMillis).toBe(at(14, 8))
  })

  it('a window crossing midnight stays on into the next morning', () => {
    const d = decide(nightly, null, at(8, 1), JAKARTA)!
    expect(d.on).toBe(true)
    expect(d.nextChangeMillis).toBe(at(8, 2))
  })

  it('a disabled schedule decides nothing', () => {
    expect(decide({ ...weekdays, enabled: false }, null, at(7, 23), JAKARTA)).toBeNull()
  })

  it('evaluates in the zone it is given, not the browser’s own', () => {
    // 10:00 in Jakarta is 05:00 in Amsterdam (summer): before the window there.
    expect(decide(weekdays, null, at(7, 10), 'Europe/Amsterdam')!.on).toBe(false)
  })

  it('lands on the right instant across a DST change', () => {
    // Europe/Amsterdam falls back on Sunday 2026-10-25; Monday 08:00 is then UTC+1.
    const sundayNoon = Date.UTC(2026, 9, 25, 11)
    const d = decide(weekdays, null, sundayNoon, 'Europe/Amsterdam')!
    expect(d.on).toBe(false)
    expect(d.nextChangeMillis).toBe(Date.UTC(2026, 9, 26, 7))
  })
})

describe('override', () => {
  it('an unexpired override wins over the schedule, and ends at its own end', () => {
    const d = decide(weekdays, { state: 'off', until: iso(at(7, 22)) }, at(7, 15), JAKARTA)!
    expect(d.on).toBe(false)
    expect(d.source).toBe('override')
    expect(d.nextChangeMillis).toBe(at(7, 22))
  })

  it('an expired override hands back to the schedule', () => {
    const d = decide(weekdays, { state: 'on', until: iso(at(7, 8)) }, at(7, 23), JAKARTA)!
    expect(d.on).toBe(false)
    expect(d.source).toBe('schedule')
  })

  it('an override with no end is ignored while a schedule is on', () => {
    const d = decide(weekdays, { state: 'off' }, at(7, 10), JAKARTA)!
    expect(d.on).toBe(true)
    expect(d.source).toBe('schedule')
  })

  it('an override with no end stands when there is no schedule', () => {
    const d = decide(null, { state: 'off' }, at(7, 10), JAKARTA)!
    expect(d.on).toBe(false)
    expect(d.source).toBe('override')
    expect(d.nextChangeMillis).toBeNull()
  })

  it('an ended override with no schedule turns the screen back on', () => {
    const d = decide(null, { state: 'off', until: iso(at(7, 8)) }, at(7, 10), JAKARTA)!
    expect(d.on).toBe(true)
    expect(d.source).toBe('default')
  })

  it('accepts the backend’s +00:00 form as well as Z', () => {
    const d = decide(weekdays, { state: 'off', until: '2026-09-07T15:00:00+00:00' }, at(7, 15), JAKARTA)!
    expect(d.source).toBe('override')
  })

  it('nothing configured decides nothing, so power is never touched', () => {
    expect(decide(null, null, at(7, 10), JAKARTA)).toBeNull()
  })
})
