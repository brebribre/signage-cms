package com.fortu.player

import com.fortu.player.api.ManifestDevice
import com.fortu.player.api.ManifestSettings
import com.fortu.player.api.PowerOverride
import com.fortu.player.api.PowerSchedule
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneId
import java.time.ZonedDateTime

/**
 * Power as the engine actually drives it: the decision from `PowerPlanTest`, applied on the
 * screen's own clock, once per change. The clock is virtual time offset to a chosen moment, so a
 * 22:00 switch is reached in milliseconds.
 *
 * 2026-09-07 is a Monday.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class PlayerPowerTest {

    private val jakarta = ZoneId.of("Asia/Jakarta")
    private fun at(hour: Int, minute: Int = 0, second: Int = 0): Long =
        ZonedDateTime.of(2026, 9, 7, hour, minute, second, 0, jakarta).toInstant().toEpochMilli()

    private val weekdays = PowerSchedule(enabled = true, daysOfWeek = 0b0011111, powerOn = "08:00", powerOff = "22:00")

    private fun withPower(version: String, settings: ManifestSettings) =
        manifest(version = version, items = listOf(item("a"))).copy(
            device = ManifestDevice(name = "Lobby", orientation = "landscape", timezone = "Asia/Jakarta"),
            settings = settings,
        )

    private fun TestScope.engine(api: FakeApi, startMillis: Long, applied: MutableList<Boolean>) = PlayerEngine(
        api = api,
        store = FakeStore(storedToken = "t"),
        cache = FakeCache(),
        appVersion = "1.0.0",
        apiBaseUrl = "https://api.example.com",
        applyPower = { applied += it },
        clock = { startMillis + testScheduler.currentTime },
        io = UnconfinedTestDispatcher(testScheduler),
    )

    @Test
    fun `a schedule wakes the screen, then puts it to sleep at the off time`() = runTest {
        val applied = mutableListOf<Boolean>()
        val api = FakeApi().apply { manifest = withPower("v1", ManifestSettings(powerSchedule = weekdays)) }
        val e = engine(api, startMillis = at(21, 59, 30), applied = applied)
        val job = launch { e.run() }

        advanceTimeBy(1_000)
        assertEquals("on as soon as the schedule arrives", listOf(true), applied)

        advanceTimeBy(40_000) // past 22:00
        assertEquals("off at 22:00, applied once", listOf(true, false), applied)
        job.cancelAndJoin()
    }

    @Test
    fun `an override arriving in a new manifest applies straight away`() = runTest {
        val applied = mutableListOf<Boolean>()
        val api = FakeApi().apply { manifest = withPower("v1", ManifestSettings(powerSchedule = weekdays)) }
        val e = engine(api, startMillis = at(10), applied = applied)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        assertEquals(listOf(true), applied)

        // "Turn off now" in the CMS: off until the schedule's next change, 22:00 Jakarta.
        api.manifest = withPower(
            "v2",
            ManifestSettings(powerSchedule = weekdays, powerOverride = PowerOverride("off", "2026-09-07T15:00:00Z")),
        )
        advanceTimeBy(PlayerEngine.POLL_SECONDS * 1000L + 1_000)
        assertEquals(listOf(true, false), applied)
        job.cancelAndJoin()
    }

    @Test
    fun `the same decision is not re-applied on every check`() = runTest {
        val applied = mutableListOf<Boolean>()
        val api = FakeApi().apply { manifest = withPower("v1", ManifestSettings(powerSchedule = weekdays)) }
        val e = engine(api, startMillis = at(10), applied = applied)
        val job = launch { e.run() }

        advanceTimeBy(5 * 60_000L)
        assertEquals(listOf(true), applied)
        job.cancelAndJoin()
    }

    @Test
    fun `a screen with no power configured is never touched`() = runTest {
        val applied = mutableListOf<Boolean>()
        val api = FakeApi().apply { manifest = withPower("v1", ManifestSettings()) }
        val e = engine(api, startMillis = at(23), applied = applied)
        val job = launch { e.run() }

        advanceTimeBy(5 * 60_000L)
        assertTrue(applied.isEmpty())
        job.cancelAndJoin()
    }
}
