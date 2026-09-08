package com.fortu.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Tests for the player's state machine.
 *
 * Every one of these covers something that actually reached hardware. The app had no tests
 * until five real bugs had already shipped to a device — a blur handler that never fired,
 * orientation the player ignored, a boot receiver that could not work, a screen that hung on
 * the splash, and a single 401 wiping a pairing. Four of the five are state-machine
 * behaviour, which is exactly what this file pins down.
 *
 * `runTest` gives virtual time, so the engine's 30-second polls and 5-second pairing waits
 * cost nothing — the whole file runs in well under a second.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class PlayerEngineTest {

    private fun kotlinx.coroutines.test.TestScope.engine(
        api: FakeApi = FakeApi(),
        store: FakeStore = FakeStore(),
        cache: FakeCache = FakeCache(),
        canSelfUpdate: () -> Boolean = { false },
        installUpdate: (String) -> Boolean = { true },
    ) = PlayerEngine(
        api = api,
        store = store,
        cache = cache,
        appVersion = "1.0.0",
        apiBaseUrl = "https://api.example.com",
        canSelfUpdate = canSelfUpdate,
        installUpdate = installUpdate,
        // The test scheduler's dispatcher, so everything the engine does stays inside
        // virtual time and assertions never race real threads.
        io = UnconfinedTestDispatcher(testScheduler),
    )

    // --- pairing --------------------------------------------------------------------------

    @Test
    fun `an unpaired screen shows a code, not a blank screen`() = runTest {
        val api = FakeApi().apply { pollsBeforeClaim = 99 }
        val e = engine(api = api)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("expected Pairing, got $state", state is PlayerState.Pairing)
        assertEquals("ABC123", (state as PlayerState.Pairing).code)
        job.cancelAndJoin()
    }

    @Test
    fun `the pairing screen names the server it is talking to`() = runTest {
        // The single most useful line when pairing "does not work": the screen and the CMS
        // pointed at different backends is the common cause, and this is the only way to see
        // it without a laptop.
        val api = FakeApi().apply { pollsBeforeClaim = 99 }
        val e = engine(api = api)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("api.example.com", (e.state.value as PlayerState.Pairing).apiHost)
        job.cancelAndJoin()
    }

    @Test
    fun `waiting shows it is alive rather than frozen`() = runTest {
        val api = FakeApi().apply { pollsBeforeClaim = 99 }
        val e = engine(api = api)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        val first = (e.state.value as PlayerState.Pairing).checks
        advanceTimeBy(20_000)
        val later = (e.state.value as PlayerState.Pairing).checks

        assertTrue("poll count should advance ($first -> $later)", later > first)
        job.cancelAndJoin()
    }

    @Test
    fun `when a human claims it, the token is stored and success is shown`() = runTest {
        val store = FakeStore()
        val api = FakeApi().apply { pollsBeforeClaim = 1; manifest = manifest() }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(6_000)

        assertEquals("device-token", store.storedToken)
        assertEquals("Lobby", store.storedName)
        job.cancelAndJoin()
    }

    @Test
    fun `an expired code is replaced rather than shown forever`() = runTest {
        val api = FakeApi().apply { pairingExpired = true }
        val e = engine(api = api)
        val job = launch { e.run() }
        advanceTimeBy(30_000)

        assertTrue("should have requested a fresh code", api.startPairingCalls > 1)
        job.cancelAndJoin()
    }

    @Test
    fun `no network during pairing says so instead of showing an unusable code`() = runTest {
        val api = FakeApi().apply { startPairingThrows = java.io.IOException("no route") }
        val e = engine(api = api)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value as PlayerState.Pairing
        assertNotNull("an error should be shown", state.error)
        job.cancelAndJoin()
    }

    // --- the splash-hang bug --------------------------------------------------------------

    @Test
    fun `a paired screen that cannot sync shows trouble, never hangs on the splash`() = runTest {
        // The real bug: runForever caught every exception, waited, retried, and never changed
        // the visible state — so a screen with a token sat on the FORTU splash forever,
        // indistinguishable from a crash.
        val store = FakeStore(storedToken = "existing-token", storedName = "Lobby")
        val api = FakeApi()
        repeat(5) { api.manifestFailures += java.io.IOException("boom") }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("expected Trouble, got $state", state is PlayerState.Trouble)
        assertEquals("api.example.com", (state as PlayerState.Trouble).apiHost)
        job.cancelAndJoin()
    }

    @Test
    fun `trouble does not replace content that is already playing`() = runTest {
        // A single failed poll while content is on air must not blank the wall — the cached
        // loop is still the best thing to be showing, which is the point of caching.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val cache = FakeCache()
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        assertTrue("should be playing first", e.state.value is PlayerState.Playing)

        api.manifestFailures += java.io.IOException("transient")
        advanceTimeBy(35_000)

        assertTrue(
            "content must survive a failed poll, got ${e.state.value}",
            e.state.value is PlayerState.Playing,
        )
        job.cancelAndJoin()
    }

    // --- the token-wipe bug ---------------------------------------------------------------

    @Test
    fun `one 401 does not unpair a working screen`() = runTest {
        // Wiping the token is irreversible from the device — somebody has to walk to the
        // screen. A request landing mid-deploy must not cost that.
        val store = FakeStore(storedToken = "t", storedName = "Lobby")
        val api = FakeApi()
        api.manifestFailures += unauthorized()
        api.manifest = manifest()
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("token must survive one rejection", "t", store.storedToken)
        assertEquals(0, store.clearCount)
        job.cancelAndJoin()
    }

    @Test
    fun `repeated 401s do unpair, so a real revocation still takes effect`() = runTest {
        val store = FakeStore(storedToken = "t", storedName = "Lobby")
        val api = FakeApi()
        repeat(5) { api.manifestFailures += unauthorized() }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(120_000)

        assertTrue("a genuine revocation must eventually re-pair", store.clearCount >= 1)
        job.cancelAndJoin()
    }

    // --- manifest handling ------------------------------------------------------------------

    @Test
    fun `content downloads before it is shown, and eviction happens after`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache()
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"), item("b"))) }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals(listOf("a", "b"), cache.downloaded)
        // Evicting before the new set is safely on disk would leave a screen half-empty if
        // the network died mid-swap.
        assertEquals(setOf("a", "b"), cache.lastEvictKeep?.toSet())
        assertTrue(e.state.value is PlayerState.Playing)
        job.cancelAndJoin()
    }

    @Test
    fun `an item that fails to download does not stop the rest of the loop`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache().apply { downloadThrowsFor = "b" }
        val api = FakeApi().apply {
            manifest = manifest(items = listOf(item("a"), item("b"), item("c")))
        }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("should still play what it has, got $state", state is PlayerState.Playing)
        assertEquals(
            "only the good items play",
            listOf("a", "c"),
            (state as PlayerState.Playing).items.map { it.checksum },
        )
        job.cancelAndJoin()
    }

    @Test
    fun `a screen with no playlist idles rather than erroring`() = runTest {
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = emptyList(), playlist = null) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("expected Idle, got $state", state is PlayerState.Idle)
        assertEquals("Lobby", (state as PlayerState.Idle).deviceName)
        job.cancelAndJoin()
    }

    // --- the orientation bug ----------------------------------------------------------------

    @Test
    fun `orientation from the manifest reaches the state the UI reads`() = runTest {
        // The bug this replaces: the CMS could set portrait, the manifest carried it, the
        // version hash changed — and the player ignored the value entirely. A server-side
        // test cannot see the client discarding it.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest(items = listOf(item("a")), orientation = "portrait")
        }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("portrait", (e.state.value as PlayerState.Playing).orientation)
        job.cancelAndJoin()
    }

    @Test
    fun `orientation also reaches an idle screen`() = runTest {
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest(items = emptyList(), playlist = null, orientation = "landscape")
        }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("landscape", (e.state.value as PlayerState.Idle).orientation)
        job.cancelAndJoin()
    }

    // --- version skew -------------------------------------------------------------------------

    @Test
    fun `a 304 leaves the current content alone`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache()
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        val before = e.state.value

        api.manifestReturns304 = true
        advanceTimeBy(35_000)

        assertTrue(e.state.value is PlayerState.Playing)
        assertEquals(
            "nothing should be re-downloaded when nothing changed",
            listOf("a"),
            cache.downloaded,
        )
        job.cancelAndJoin()
    }

    // --- proof of play ------------------------------------------------------------------------

    @Test
    fun `reported plays are batched onto the next heartbeat`() = runTest {
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        e.reportPlay(item("a"), startedAtMillis = 1_000_000, seconds = 10)
        e.reportPlay(item("b"), startedAtMillis = 1_010_000, seconds = 12)
        advanceTimeBy(35_000)

        val withPlays = api.heartbeats.firstOrNull { it.plays.isNotEmpty() }
        assertNotNull("plays should be sent on a heartbeat", withPlays)
        assertEquals(2, withPlays!!.plays.size)
        assertEquals("media-a", withPlays.plays[0].mediaId)
        job.cancelAndJoin()
    }

    @Test
    fun `plays are drained, not resent forever`() = runTest {
        // A screen retrying a growing backlog on every beat would be worse than a gap.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        e.reportPlay(item("a"), 1_000_000, 10)
        advanceTimeBy(35_000)
        advanceTimeBy(35_000)

        val beatsWithPlays = api.heartbeats.count { it.plays.isNotEmpty() }
        assertEquals("the same play must not be sent twice", 1, beatsWithPlays)
        job.cancelAndJoin()
    }

    // --- self update ---------------------------------------------------------------------------

    @Test
    fun `an update is not attempted on a device that cannot install silently`() = runTest {
        // Falling back to the interactive installer would park a screen on a permission
        // prompt nobody is standing in front of.
        var installs = 0
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk"),
            )
        }
        val e = engine(
            api = api, store = store,
            canSelfUpdate = { false },
            installUpdate = { installs++; true },
        )
        val job = launch { e.run() }
        advanceTimeBy(35_000)

        assertEquals(0, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `a failed update is not retried on every heartbeat`() = runTest {
        // Otherwise a bad APK becomes a 30-second re-download loop.
        var installs = 0
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk"),
            )
        }
        val e = engine(
            api = api, store = store,
            canSelfUpdate = { true },
            installUpdate = { installs++; false },
        )
        val job = launch { e.run() }
        advanceTimeBy(180_000)

        assertEquals("one attempt per app run", 1, installs)
        job.cancelAndJoin()
    }
}
