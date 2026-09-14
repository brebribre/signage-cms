package com.fortu.player

import com.fortu.player.api.PowerOverride
import com.fortu.player.api.PowerSchedule
import com.fortu.player.power.PowerPlan
import com.fortu.player.power.PowerPlan.Source
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneId
import java.time.ZonedDateTime

/**
 * The power rules, pinned. Mirrors `backend/scripts/check_power.py` — the CMS shows what these
 * decide, so the two must agree case for case.
 *
 * 2026-09-07 is a Monday.
 */
class PowerPlanTest {

    private val jakarta = ZoneId.of("Asia/Jakarta")
    private fun at(day: Int, hour: Int, minute: Int = 0): Long =
        ZonedDateTime.of(2026, 9, day, hour, minute, 0, 0, jakarta).toInstant().toEpochMilli()
    private fun iso(millis: Long) = java.time.Instant.ofEpochMilli(millis).toString()

    private val weekdays = PowerSchedule(enabled = true, daysOfWeek = 0b0011111, powerOn = "08:00", powerOff = "22:00")
    private val nightly = PowerSchedule(enabled = true, daysOfWeek = 0b1111111, powerOn = "20:00", powerOff = "02:00")

    // --- schedule --------------------------------------------------------------------------

    @Test
    fun `inside the window is on, and the next change is the off time`() {
        val d = PowerPlan.decide(weekdays, null, at(7, 10), jakarta)!!
        assertTrue(d.on)
        assertEquals(Source.SCHEDULE, d.source)
        assertEquals(at(7, 22), d.nextChangeMillis)
    }

    @Test
    fun `after the off time is off until the next morning`() {
        val d = PowerPlan.decide(weekdays, null, at(7, 23), jakarta)!!
        assertFalse(d.on)
        assertEquals(at(8, 8), d.nextChangeMillis)
    }

    @Test
    fun `the start is inclusive and the end exclusive`() {
        assertTrue(PowerPlan.decide(weekdays, null, at(7, 8), jakarta)!!.on)
        assertFalse(PowerPlan.decide(weekdays, null, at(7, 22), jakarta)!!.on)
    }

    @Test
    fun `an unselected day is off all day, until the next selected morning`() {
        // Saturday the 12th → Monday the 14th, skipping Sunday's edges that change nothing.
        val d = PowerPlan.decide(weekdays, null, at(12, 10), jakarta)!!
        assertFalse(d.on)
        assertEquals(at(14, 8), d.nextChangeMillis)
    }

    @Test
    fun `a window crossing midnight stays on into the next morning`() {
        val d = PowerPlan.decide(nightly, null, at(8, 1), jakarta)!!
        assertTrue(d.on)
        assertEquals(at(8, 2), d.nextChangeMillis)
    }

    @Test
    fun `a disabled schedule decides nothing`() {
        assertNull(PowerPlan.decide(weekdays.copy(enabled = false), null, at(7, 23), jakarta))
    }

    // --- override --------------------------------------------------------------------------

    @Test
    fun `an unexpired override wins over the schedule, and ends at its own end`() {
        val override = PowerOverride(state = "off", until = iso(at(7, 22)))
        val d = PowerPlan.decide(weekdays, override, at(7, 15), jakarta)!!
        assertFalse(d.on)
        assertEquals(Source.OVERRIDE, d.source)
        assertEquals(at(7, 22), d.nextChangeMillis)
    }

    @Test
    fun `an expired override hands back to the schedule`() {
        val override = PowerOverride(state = "on", until = iso(at(7, 8)))
        val d = PowerPlan.decide(weekdays, override, at(7, 23), jakarta)!!
        assertFalse(d.on)
        assertEquals(Source.SCHEDULE, d.source)
    }

    @Test
    fun `an override with no end is ignored while a schedule is on`() {
        val d = PowerPlan.decide(weekdays, PowerOverride(state = "off"), at(7, 10), jakarta)!!
        assertTrue(d.on)
        assertEquals(Source.SCHEDULE, d.source)
    }

    @Test
    fun `an override with no end stands when there is no schedule`() {
        val d = PowerPlan.decide(null, PowerOverride(state = "off"), at(7, 10), jakarta)!!
        assertFalse(d.on)
        assertEquals(Source.OVERRIDE, d.source)
        assertNull(d.nextChangeMillis)
    }

    @Test
    fun `an ended override with no schedule turns the screen back on`() {
        val d = PowerPlan.decide(null, PowerOverride(state = "off", until = iso(at(7, 8))), at(7, 10), jakarta)!!
        assertTrue(d.on)
        assertEquals(Source.DEFAULT, d.source)
    }

    @Test
    fun `nothing configured decides nothing, so power is never touched`() {
        assertNull(PowerPlan.decide(null, null, at(7, 10), jakarta))
    }
}
