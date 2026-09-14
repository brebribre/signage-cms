package com.fortu.player.power

import com.fortu.player.api.PowerOverride
import com.fortu.player.api.PowerSchedule
import java.time.Instant
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime

/**
 * Whether the screen should be on right now: its weekly power schedule plus a temporary manual
 * override. Pure — no Android, no clock of its own — so it is tested on a plain JVM.
 *
 * **This is where power is actually decided.** The CMS never commands "off" directly; it sends
 * the schedule and any override, and the screen works the answer out on its own clock — so it
 * still goes dark at 22:00 with no network at 22:00. The backend keeps a copy of exactly these
 * rules (`backend/app/services/power.py`) to show what a screen should be doing; the two must
 * stay in step.
 *
 * The rules, in order:
 * 1. An override that hasn't ended wins. An override with no end only counts while there is no
 *    schedule — enabling a schedule must never be silently blocked by an old manual setting.
 * 2. Otherwise an enabled schedule decides: on inside the day's window, off outside it, and off
 *    all day on days that aren't selected. A window ending before it starts runs through
 *    midnight and belongs to the day it starts on.
 * 3. Otherwise the screen is on — but only once power has been configured at all. A screen
 *    nobody has touched gets no decision, so this build never changes power on its own.
 */
object PowerPlan {

    enum class Source { OVERRIDE, SCHEDULE, DEFAULT }

    /** [nextChangeMillis] is when this answer stops being true on its own, if ever. */
    data class Decision(val on: Boolean, val source: Source, val nextChangeMillis: Long?)

    /** A week covers every pattern; the extra day covers a window crossing midnight. */
    private const val LOOKAHEAD_DAYS = 8L

    fun decide(schedule: PowerSchedule?, override: PowerOverride?, nowMillis: Long, zone: ZoneId): Decision? {
        val hasSchedule = schedule?.enabled == true
        val local = Instant.ofEpochMilli(nowMillis).atZone(zone)

        if (override != null && (override.state == "on" || override.state == "off")) {
            val on = override.state == "on"
            if (override.until == null) {
                if (!hasSchedule) return Decision(on, Source.OVERRIDE, null)
            } else {
                val until = parseInstantMillis(override.until)
                if (until != null && nowMillis < until) return Decision(on, Source.OVERRIDE, until)
            }
        }

        if (hasSchedule) {
            return Decision(scheduledOn(schedule!!, local), Source.SCHEDULE, nextChangeMillis(schedule, local))
        }

        // An override existed but has ended, and there is no schedule to fall back on.
        return if (override != null) Decision(true, Source.DEFAULT, null) else null
    }

    fun scheduledOn(schedule: PowerSchedule, local: ZonedDateTime): Boolean {
        val on = LocalTime.parse(schedule.powerOn)
        val off = LocalTime.parse(schedule.powerOff)
        val t = local.toLocalTime()
        val weekday = local.dayOfWeek.value - 1 // Monday = 0, matching the bitmask
        fun selected(day: Int) = schedule.daysOfWeek and (1 shl ((day + 7) % 7)) != 0

        if (on < off) return selected(weekday) && t >= on && t < off
        // Crosses midnight: late on a selected day, or early the morning after one.
        if (t >= on) return selected(weekday)
        if (t < off) return selected(weekday - 1)
        return false
    }

    /** The next moment the schedule's answer actually flips, skipping edges that change nothing
     *  (an off time on a day the screen is already off). */
    fun nextChangeMillis(schedule: PowerSchedule, local: ZonedDateTime): Long? {
        val current = scheduledOn(schedule, local)
        val edges = listOf(LocalTime.parse(schedule.powerOn), LocalTime.parse(schedule.powerOff))
        return (0 until LOOKAHEAD_DAYS)
            .flatMap { offset -> edges.map { ZonedDateTime.of(local.toLocalDate().plusDays(offset), it, local.zone) } }
            .sortedBy { it.toInstant() }
            .firstOrNull { it.isAfter(local) && scheduledOn(schedule, it) != current }
            ?.toInstant()
            ?.toEpochMilli()
    }

    fun parseInstantMillis(iso: String): Long? =
        runCatching { Instant.parse(iso.replace("+00:00", "Z")).toEpochMilli() }.getOrNull()
}
