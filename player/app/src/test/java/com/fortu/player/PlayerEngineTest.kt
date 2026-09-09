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
        push: PushClient = NoopPushClient,
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
        push = push,
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

    @Test
    fun `an admin unpairing or deleting a screen sees it re-pair within seconds, not minutes`() = runTest {
        // The retries that confirm a 401 is real must not ride the ordinary 30s poll cadence —
        // an admin who just clicked Unpair or Delete is watching the screen, and three
        // five-second confirmations settle it in well under 20 seconds instead of ~90.
        val store = FakeStore(storedToken = "t", storedName = "Lobby")
        val api = FakeApi()
        repeat(5) { api.manifestFailures += unauthorized() }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(20_000)

        assertTrue("must re-pair within 20s, not the old ~90s", store.clearCount >= 1)
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

    // --- restart / power cut ------------------------------------------------------------------

    @Test
    fun `a restarted screen plays again even though the server answers 304`() = runTest {
        // The bug: the ETag was persisted across a restart but the content was not, so on boot
        // the server correctly said "nothing changed" and the player — which had just started
        // and had nothing in memory — sat on the splash until somebody edited the playlist.
        val m = manifest(version = "v9", items = listOf(item("a")))
        val store = FakeStore(
            storedToken = "t",
            storedEtag = "\"v9\"",
            storedManifestJson = kotlinx.serialization.json.Json.encodeToString(
                com.fortu.player.api.Manifest.serializer(), m,
            ),
        )
        val cache = FakeCache().apply { cached += "a" }
        val api = FakeApi().apply {
            manifest = m
            honourEtag = true
            // Consistent with the manifest, or the heartbeat's "version moved under us" fast
            // path fires on every single beat and this test stops exercising restart/304 at
            // all — it starts exercising an unrelated race with no delay between iterations.
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(version = "v9")
        }

        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("a rebooted screen must play, got $state", state is PlayerState.Playing)
        assertEquals(listOf("a"), (state as PlayerState.Playing).items.map { it.checksum })
        job.cancelAndJoin()
    }

    @Test
    fun `a restarted screen plays from cache with no network at all`() = runTest {
        // The case that matters after a power cut: the screen comes back before the router
        // does. The files are on disk; this is the only thing that knows which to play.
        val m = manifest(version = "v9", items = listOf(item("a"), item("b")))
        val store = FakeStore(
            storedToken = "t",
            storedManifestJson = kotlinx.serialization.json.Json.encodeToString(
                com.fortu.player.api.Manifest.serializer(), m,
            ),
        )
        val cache = FakeCache().apply { cached += "a"; cached += "b" }
        val api = FakeApi()
        repeat(10) { api.manifestFailures += java.io.IOException("network down") }

        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("must play offline from cache, got $state", state is PlayerState.Playing)
        assertEquals(2, (state as PlayerState.Playing).items.size)
        job.cancelAndJoin()
    }

    @Test
    fun `with nothing restored, no ETag is sent so the server must answer in full`() = runTest {
        val store = FakeStore(storedToken = "t", storedEtag = "\"stale\"")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertNull("first fetch after a restart must not be conditional", api.etagsSeen.first())
        assertTrue(e.state.value is PlayerState.Playing)
        job.cancelAndJoin()
    }

    @Test
    fun `once playing, the ETag is sent again so polls stay cheap`() = runTest {
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        advanceTimeBy(35_000)

        assertNotNull(
            "later polls must be conditional, or every screen re-downloads its manifest forever",
            api.etagsSeen.last(),
        )
        job.cancelAndJoin()
    }

    @Test
    fun `an unreadable stored manifest is ignored rather than fatal`() = runTest {
        // Written by an older build with a shape this one cannot parse.
        val store = FakeStore(storedToken = "t", storedManifestJson = "{ not json at all")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertTrue("should recover via the normal fetch", e.state.value is PlayerState.Playing)
        job.cancelAndJoin()
    }

    // --- push notifications (MQTT prototype, backend/app/infra/mqtt.py) --------------------

    @Test
    fun `a stored device id connects the push channel`() = runTest {
        val store = FakeStore(storedToken = "t", storedDeviceId = "dev-42")
        val api = FakeApi().apply { manifest = manifest() }
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertTrue("should connect using the persisted device id", push.connectedTo.isNotEmpty())
        assertTrue(push.connectedTo.all { it == "dev-42" })
        job.cancelAndJoin()
    }

    @Test
    fun `pairing saves the device id so a freshly paired screen can push-connect too`() = runTest {
        // Before this, poll.deviceId was read off the pairing response and thrown away —
        // nothing persisted it, so a screen had no id to subscribe with until it happened to
        // be unpaired and re-paired by a build that saves one.
        val api = FakeApi().apply { pollsBeforeClaim = 1 }
        val store = FakeStore()
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(10_000)

        assertEquals("dev-1", store.storedDeviceId)
        assertTrue("should connect once paired", push.connectedTo.contains("dev-1"))
        job.cancelAndJoin()
    }

    @Test
    fun `a push wakes the poll loop instead of waiting the full interval`() = runTest {
        val store = FakeStore(storedToken = "t", storedDeviceId = "dev-1")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val callsBeforePush = api.manifestCalls
        push.push()
        advanceTimeBy(1_000)

        assertTrue(
            "a push should trigger another fetch well before the 30s poll interval",
            api.manifestCalls > callsBeforePush,
        )
        job.cancelAndJoin()
    }

    @Test
    fun `a screen with no push connection behaves exactly as it always has`() = runTest {
        // The default is NoopPushClient — nothing to connect to, nothing ever emitted. This
        // pins that the poll loop's timing is unaffected when push is unavailable, which is
        // every screen running today until this ships.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val callsAfterFirstPoll = api.manifestCalls
        advanceTimeBy(29_000)
        assertEquals("must not poll again before ~30s", callsAfterFirstPoll, api.manifestCalls)
        advanceTimeBy(2_000)
        assertTrue("must poll again once ~30s has passed", api.manifestCalls > callsAfterFirstPoll)
        job.cancelAndJoin()
    }

    @Test
    fun `push disconnects when the token is cleared for re-pairing`() = runTest {
        val store = FakeStore(storedToken = "t", storedDeviceId = "dev-1", storedName = "Lobby")
        val api = FakeApi()
        repeat(5) { api.manifestFailures += unauthorized() }
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(20_000)

        assertTrue("push must disconnect once the token is cleared", push.disconnectCount >= 1)
        job.cancelAndJoin()
    }
}
