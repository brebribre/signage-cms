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
        installUpdate: (com.fortu.player.api.UpdateInfo, (Long, Long?) -> Unit) -> InstallResult =
            { _, _ -> InstallResult.HandedOver },
        consumeInstallFailure: () -> String? = { null },
        push: PushClient = NoopPushClient,
        warmMedia: suspend (java.io.File, String) -> Unit = { _, _ -> },
        // Virtual time, like everything else here: the stall watchdog, download speed and the
        // update backoff all read the clock, and a wall clock would make them untestable.
        clock: () -> Long = { testScheduler.currentTime },
        detectMount: () -> String? = { null },
    ) = PlayerEngine(
        api = api,
        store = store,
        cache = cache,
        appVersion = "1.0.0",
        apiBaseUrl = "https://api.example.com",
        canSelfUpdate = canSelfUpdate,
        installUpdate = installUpdate,
        consumeInstallFailure = consumeInstallFailure,
        warmMedia = warmMedia,
        // The test scheduler's dispatcher, so everything the engine does stays inside
        // virtual time and assertions never race real threads.
        io = UnconfinedTestDispatcher(testScheduler),
        push = push,
        clock = clock,
        detectMount = detectMount,
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
    fun `the screen's own mounting goes with the code, and with every check while it waits`() = runTest {
        val api = FakeApi().apply { pollsBeforeClaim = 3; manifest = manifest() }
        var reading = "270"
        val e = engine(api = api, detectMount = { reading })
        val job = launch { e.run() }
        advanceTimeBy(6_000)
        reading = "90" // lifted onto the wall while the code was up
        advanceTimeBy(12_000)

        assertEquals("270", api.detectedOrientations.first())
        assertEquals("90", api.detectedOrientations.last())
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

    @Test
    fun `a screen the CMS disconnects re-pairs at once and forgets the account`() = runTest {
        // 410 is deliberate, unlike a 401 — no three-strikes wait, and nothing of the old
        // account survives: token, cached content, push subscription, pending reports.
        val store = FakeStore(storedToken = "t", storedName = "Lobby", storedDeviceId = "dev-1", storedMqttPassword = "pw")
        val cache = FakeCache().apply { cached += "a" }
        val push = FakePushClient()
        val api = FakeApi().apply {
            manifest = manifest(items = listOf(item("a")))
            pollsBeforeClaim = 99
        }
        val e = engine(api = api, store = store, cache = cache, push = push)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        e.reportError("stale")
        api.manifestFailures += disconnected()
        advanceTimeBy(35_000)

        assertEquals("token dropped on the first 410", 1, store.clearCount)
        assertEquals("cached content of the old account evicted", emptyList<String>(), cache.lastEvictKeep?.toList())
        assertEquals("push subscription dropped", 1, push.disconnectCount)
        assertNull(e.orientation.value)
        assertTrue("back to pairing, not trouble: ${e.state.value}", e.state.value is PlayerState.Pairing)
        // The report queued for the old account never reaches the new one.
        api.heartbeats.clear()
        job.cancelAndJoin()
    }

    @Test
    fun `dropped frames and the decoder ride the next heartbeat, and the count is drained`() = runTest {
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply { manifest = manifest() }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        e.reportVideoStats(3, "OMX.test.avc")
        e.reportVideoStats(2, null)
        advanceTimeBy(35_000)

        val beat = api.heartbeats.last().playback
        assertEquals(5, beat?.droppedFrames)
        assertEquals("OMX.test.avc", beat?.decoder)
        assertEquals(5, e.debug.value.droppedFrames)

        advanceTimeBy(35_000)
        val next = api.heartbeats.last().playback
        assertEquals("a delta, not a running total", 0, next?.droppedFrames)
        assertEquals("the decoder is a fact about the box, not the beat", "OMX.test.avc", next?.decoder)
        job.cancelAndJoin()
    }

    @Test
    fun `a loop that stops reporting plays is restarted, and one that keeps playing is left alone`() = runTest {
        val store = FakeStore(storedToken = "t")
        // Like the real server: 304 on every poll while nothing changes. The fake's default of
        // re-sending the manifest would re-apply it (and so re-arm the watchdog) every 30s.
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"), item("b"))); honourEtag = true }
        val e = engine(api = api, store = store)
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        val playing = e.state.value as PlayerState.Playing
        assertEquals(0, playing.generation)

        // Plays keep arriving: generation stays put across many polls.
        repeat(6) {
            e.reportPlay(playing.slots[0], 0, 10)
            advanceTimeBy(30_000)
        }
        assertEquals(0, (e.state.value as PlayerState.Playing).generation)

        // Silence for longer than any slot could last: the surface is rebuilt and the CMS told.
        advanceTimeBy(4 * 60_000)
        assertEquals(1, (e.state.value as PlayerState.Playing).generation)
        assertTrue(api.heartbeats.any { beat -> beat.errors.any { it.contains("stalled") } })
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
            (state as PlayerState.Playing).elements.map { it.checksum },
        )
        job.cancelAndJoin()
    }

    @Test
    fun `everything about to play is warmed before the switch, and nothing else is`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache().apply { downloadThrowsFor = "b" }
        val warmed = mutableListOf<String>()
        val api = FakeApi().apply {
            manifest = manifest(items = listOf(item("a"), item("b", kind = "video"), item("c")))
        }
        val e = engine(
            api = api, store = store, cache = cache,
            warmMedia = { file, kind -> warmed += "$kind:${file.name}" },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        // "b" failed to download, so its slot never plays and is never warmed either — warming
        // something that will not be shown would just be wasted work.
        assertEquals(listOf("image:a", "image:c"), warmed)
        job.cancelAndJoin()
    }

    @Test
    fun `warming a file does not stop playback if it throws`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache()
        val api = FakeApi().apply { manifest = manifest(items = listOf(item("a"))) }
        val e = engine(
            api = api, store = store, cache = cache,
            warmMedia = { _, _ -> throw java.io.IOException("warm-up failed") },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertTrue(e.state.value is PlayerState.Playing)
        job.cancelAndJoin()
    }

    // --- multi-element slots (real `slots`, not the flattened `items`) --------------------

    @Test
    fun `every element of a multi-element slot downloads before it plays`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache()
        val api = FakeApi().apply {
            manifest = manifest(slots = listOf(slot(item("a"), item("b"))))
        }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals(setOf("a", "b"), cache.downloaded.toSet())
        val state = e.state.value
        assertTrue(state is PlayerState.Playing)
        assertEquals(1, (state as PlayerState.Playing).slots.size)
        assertEquals(2, state.slots.single().elements.size)
        job.cancelAndJoin()
    }

    @Test
    fun `a slot is not playable until every one of its elements is cached`() = runTest {
        // One bad layer must drop the whole scene, not show it missing a piece — a half-drawn
        // scene is a worse failure than skipping it for one that plays cleanly.
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache().apply { downloadThrowsFor = "b" }
        val api = FakeApi().apply {
            manifest = manifest(
                slots = listOf(
                    slot(item("a"), item("b")), // one element fails — the whole slot drops
                    slot(item("c")), // unaffected
                ),
            )
        }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val state = e.state.value
        assertTrue("the unaffected slot should still play, got $state", state is PlayerState.Playing)
        assertEquals(
            "only the fully-cached slot survives",
            listOf("c"),
            (state as PlayerState.Playing).elements.map { it.checksum },
        )
        job.cancelAndJoin()
    }

    @Test
    fun `a website element plays without downloading anything`() = runTest {
        val store = FakeStore(storedToken = "t")
        val cache = FakeCache()
        val website = com.fortu.player.api.ManifestElement(
            id = "el-web",
            kind = com.fortu.player.api.KIND_WEB,
            url = "https://example.com/menu",
            checksum = "web-abc",
            bytes = 0,
        )
        val api = FakeApi().apply {
            manifest = manifest(
                slots = listOf(
                    slot(item("a")),
                    com.fortu.player.api.ManifestSlot(id = "slot-web", durationSeconds = 30, elements = listOf(website)),
                ),
            )
        }
        val e = engine(api = api, store = store, cache = cache)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("only the file downloads", listOf("a"), cache.downloaded)
        val state = e.state.value
        assertTrue("both slots should play, got $state", state is PlayerState.Playing)
        assertEquals(2, (state as PlayerState.Playing).slots.size)
        org.junit.Assert.assertFalse(
            "a website is never kept in the file cache",
            cache.lastEvictKeep!!.contains("web-abc"),
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

        assertEquals("portrait", e.orientation.value)
        job.cancelAndJoin()
    }

    @Test
    fun `a rotation does not wait for the content pipeline`() = runTest {
        // The bug this replaces: orientation rode on the PlayerState emitted at the *end* of
        // applyManifest — after every element had been downloaded and warmed, and warming a
        // video reads the whole file. A screen told to rotate kept the old orientation until
        // all of that finished, which on a panel carrying a large video looks like the CMS
        // simply not working.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest(items = listOf(item("a")), orientation = "portrait")
        }
        val e = engine(
            api = api, store = store,
            warmMedia = { _, _ -> kotlinx.coroutines.delay(60_000) },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals("portrait", e.orientation.value)
        assertTrue(
            "content should still be preparing, or this proves nothing",
            e.state.value !is PlayerState.Playing,
        )
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

        assertEquals("landscape", e.orientation.value)
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

        e.reportPlay(slot(item("a")), startedAtMillis = 1_000_000, seconds = 10)
        e.reportPlay(slot(item("b")), startedAtMillis = 1_010_000, seconds = 12)
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

        e.reportPlay(slot(item("a")), 1_000_000, 10)
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
            installUpdate = { _, _ -> installs++; InstallResult.HandedOver },
        )
        val job = launch { e.run() }
        advanceTimeBy(35_000)

        assertEquals(0, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `a failed update is not retried on every heartbeat`() = runTest {
        // Otherwise a bad APK becomes a 30-second re-download loop. It does back off and
        // retry eventually (PlayerEngine.UPDATE_RETRY_COOLDOWN_MILLIS) — just not this fast.
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
            installUpdate = { _, _ -> installs++; InstallResult.Failed("download failed: timeout") },
        )
        val job = launch { e.run() }
        advanceTimeBy(180_000)

        assertEquals("no retry within the cooldown window", 1, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `an update the system rejects afterwards is not retried on every heartbeat`() = runTest {
        // The dangerous case, and the one that actually happens: handing the APK to
        // PackageInstaller succeeds, and the rejection (no space, wrong signature, a
        // downgrade) only comes back by broadcast afterwards. Judged on the hand-off alone
        // this looks like success, so nothing backed off and the screen re-downloaded the
        // same doomed build every 30 seconds — observed on the emulator before this existed.
        var installs = 0
        var rejected = false
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
            installUpdate = { _, _ -> installs++; rejected = true; InstallResult.HandedOver },
            consumeInstallFailure = { if (rejected) { rejected = false; "not enough free space" } else null },
        )
        val job = launch { e.run() }
        advanceTimeBy(180_000)

        assertEquals("a rejection reported by broadcast must start the same backoff", 1, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `a different version is retried immediately, even mid-cooldown`() = runTest {
        // A newer rollout (or a rollback) after a failed attempt must not sit behind the
        // cooldown meant for retrying the *same* failed download.
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
            installUpdate = { _, _ -> installs++; InstallResult.Failed("download failed: timeout") },
        )
        val job = launch { e.run() }
        advanceTimeBy(35_000)
        assertEquals(1, installs)

        api.heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
            version = "v1",
            update = com.fortu.player.api.UpdateInfo("2.0.1", "https://fake/app2.apk"),
        )
        advanceTimeBy(35_000)

        assertEquals("2.0.1 is a different download than the one that just failed", 2, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `download progress and the hand-off are reported to the server`() = runTest {
        // The CMS's whole view of an install comes from these reports — before they existed
        // it could only say "pending" until the version happened to change.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk", bytes = 1000),
            )
        }
        val e = engine(
            api = api, store = store,
            canSelfUpdate = { true },
            installUpdate = { _, onProgress ->
                onProgress(500, 1000)
                onProgress(1000, 1000)
                InstallResult.HandedOver
            },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val reports = api.updateReports.map { Triple(it.state, it.progressPct, it.version) }
        assertEquals(
            listOf(
                Triple("downloading", 0, "2.0.0"),
                Triple("downloading", 50, "2.0.0"),
                Triple("downloading", 100, "2.0.0"),
                Triple("installing", 100, "2.0.0"),
            ),
            reports,
        )
        assertEquals(UpdatePhase.INSTALLING, e.debug.value.update?.phase)
        job.cancelAndJoin()
    }

    @Test
    fun `a failed download tells the server why`() = runTest {
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
            installUpdate = { _, _ -> InstallResult.Failed("download failed after 3 attempts (timeout)") },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        val last = api.updateReports.last()
        assertEquals("failed", last.state)
        assertEquals("download failed after 3 attempts (timeout)", last.detail)
        assertEquals(UpdatePhase.FAILED, e.debug.value.update?.phase)
        job.cancelAndJoin()
    }

    @Test
    fun `a report that cannot be sent does not fail the update`() = runTest {
        // The report is about the update; it must never be able to break it.
        var installs = 0
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk"),
            )
            updateReportThrows = java.io.IOException("cms unreachable")
        }
        val e = engine(
            api = api, store = store,
            canSelfUpdate = { true },
            installUpdate = { _, _ -> installs++; InstallResult.HandedOver },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertEquals(1, installs)
        assertEquals(UpdatePhase.INSTALLING, e.debug.value.update?.phase)
        job.cancelAndJoin()
    }

    @Test
    fun `the same version offered again from the CMS is retried at once, mid-cooldown`() = runTest {
        // "Retry now" on the Screens page re-issues the pin with a fresh requested_at. The
        // unchanged offer on every heartbeat after a failure still waits out the cooldown.
        var installs = 0
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo(
                    "2.0.0", "https://fake/app.apk", requestedAt = "2026-09-17T10:00:00Z",
                ),
            )
        }
        val e = engine(
            api = api, store = store,
            canSelfUpdate = { true },
            installUpdate = { _, _ -> installs++; InstallResult.Failed("boom") },
        )
        val job = launch { e.run() }
        advanceTimeBy(65_000)
        assertEquals("the unchanged offer backs off", 1, installs)

        api.heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
            version = "v1",
            update = com.fortu.player.api.UpdateInfo(
                "2.0.0", "https://fake/app.apk", requestedAt = "2026-09-17T10:05:00Z",
            ),
        )
        advanceTimeBy(35_000)

        assertEquals("a re-issued offer is a new request", 2, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `a screen that cannot self-install says so to the server, once`() = runTest {
        // From the CMS, "pending forever" and "will never happen" otherwise look the same —
        // and only one of them is fixed by waiting.
        val store = FakeStore(storedToken = "t")
        val api = FakeApi().apply {
            manifest = manifest()
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk"),
            )
        }
        val e = engine(api = api, store = store, canSelfUpdate = { false })
        val job = launch { e.run() }
        advanceTimeBy(100_000)

        assertEquals(1, api.updateReports.size)
        assertEquals("failed", api.updateReports[0].state)
        assertEquals(PlayerEngine.NOT_DEVICE_OWNER_REASON, api.updateReports[0].detail)
        assertNull("not a banner-worthy failure on screen", e.debug.value.update)
        job.cancelAndJoin()
    }

    @Test
    fun `an installer rejection reaches the server without waiting for a heartbeat`() = runTest {
        var rejected = false
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
            installUpdate = { _, _ -> InstallResult.HandedOver },
            consumeInstallFailure = { if (rejected) { rejected = false; "not enough free space" } else null },
        )
        val job = launch { e.run() }
        advanceTimeBy(1_000)
        assertEquals("installing", api.updateReports.last().state)

        // The broadcast lands; the ViewModel forwards it straight away.
        rejected = true
        e.onInstallVerdict()

        val last = api.updateReports.last()
        assertEquals("failed", last.state)
        assertEquals("not enough free space", last.detail)
        assertEquals(UpdatePhase.FAILED, e.debug.value.update?.phase)
        job.cancelAndJoin()
    }

    @Test
    fun `checking for an update manually reports up to date when there is nothing to install`() = runTest {
        val api = FakeApi().apply {
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(version = "v1", update = null)
        }
        val e = engine(api = api, store = FakeStore(storedToken = "t"), canSelfUpdate = { true })

        e.checkForUpdateNow()

        assertEquals("up to date (1.0.0)", e.debug.value.updateStatus)
    }

    @Test
    fun `checking for an update manually installs immediately, ignoring any cooldown`() = runTest {
        // The whole point of the on-screen button: someone standing at the device asking for
        // this explicitly should never hear "try again in ten minutes."
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
            installUpdate = { _, _ -> installs++; InstallResult.Failed("download failed: timeout") },
        )
        val job = launch { e.run() }
        advanceTimeBy(35_000)
        assertEquals("the automatic attempt used up the install", 1, installs)

        e.checkForUpdateNow()

        assertEquals("the manual check tried again despite the cooldown", 2, installs)
        job.cancelAndJoin()
    }

    @Test
    fun `checking for an update manually declines on a device that cannot self-install`() = runTest {
        var installs = 0
        val api = FakeApi().apply {
            heartbeatResponse = com.fortu.player.api.HeartbeatResponse(
                version = "v1",
                update = com.fortu.player.api.UpdateInfo("2.0.0", "https://fake/app.apk"),
            )
        }
        val e = engine(
            api = api, store = FakeStore(storedToken = "t"),
            canSelfUpdate = { false },
            installUpdate = { _, _ -> installs++; InstallResult.HandedOver },
        )

        e.checkForUpdateNow()

        assertEquals(0, installs)
        assertEquals(
            "2.0.0 available, but this screen can't self-install",
            e.debug.value.updateStatus,
        )
    }

    @Test
    fun `checking for an update manually surfaces a heartbeat failure instead of hanging`() = runTest {
        val api = FakeApi().apply { heartbeatThrows = java.io.IOException("no network") }
        val e = engine(api = api, store = FakeStore(storedToken = "t"), canSelfUpdate = { true })

        e.checkForUpdateNow()

        assertEquals("check failed: no network", e.debug.value.updateStatus)
    }

    @Test
    fun `checking for an update manually before pairing does not crash`() = runTest {
        val e = engine(store = FakeStore(storedToken = null))

        e.checkForUpdateNow()

        assertEquals("not paired yet", e.debug.value.updateStatus)
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
        assertEquals(listOf("a"), (state as PlayerState.Playing).elements.map { it.checksum })
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
        assertEquals(2, (state as PlayerState.Playing).elements.size)
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
    fun `a stored device id and mqtt password connect the push channel`() = runTest {
        val store = FakeStore(storedToken = "t", storedDeviceId = "dev-42", storedMqttPassword = "pw-42")
        val api = FakeApi().apply { manifest = manifest() }
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertTrue("should connect using the persisted device id", push.connectedTo.isNotEmpty())
        assertTrue(push.connectedTo.all { it == "dev-42" })
        // No shared credential any more — every device connects with its own password.
        assertTrue(push.passwordsSeen.all { it == "pw-42" })
        job.cancelAndJoin()
    }

    @Test
    fun `pairing saves the device id and mqtt password so a freshly paired screen can push-connect too`() = runTest {
        // Before this, poll.deviceId was read off the pairing response and thrown away —
        // nothing persisted it, so a screen had no id to subscribe with until it happened to
        // be unpaired and re-paired by a build that saves one. mqttPassword is new for the
        // same reason: it is how a device stops sharing one broker credential with every
        // other screen and gets its own, scoped by mosquitto's device-role to its own topic.
        val api = FakeApi().apply { pollsBeforeClaim = 1; mqttPasswordOnClaim = "fresh-secret" }
        val store = FakeStore()
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(10_000)

        assertEquals("dev-1", store.storedDeviceId)
        assertEquals("fresh-secret", store.storedMqttPassword)
        assertTrue("should connect once paired", push.connectedTo.contains("dev-1"))
        assertTrue("should connect with its own freshly-issued password", push.passwordsSeen.contains("fresh-secret"))
        job.cancelAndJoin()
    }

    @Test
    fun `no mqtt password still connects — some brokers (local dev) need none`() = runTest {
        val store = FakeStore(storedToken = "t", storedDeviceId = "dev-1", storedMqttPassword = null)
        val api = FakeApi().apply { manifest = manifest() }
        val push = FakePushClient()
        val e = engine(api = api, store = store, push = push)
        val job = launch { e.run() }
        advanceTimeBy(1_000)

        assertTrue(push.connectedTo.contains("dev-1"))
        assertTrue("a missing password connects with a blank one, not a crash", push.passwordsSeen.all { it == "" })
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
