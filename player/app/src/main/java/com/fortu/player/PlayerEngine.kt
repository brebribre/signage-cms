package com.fortu.player

import android.util.Log
import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatScreen
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestSettings
import com.fortu.player.api.ManifestSlot
import com.fortu.player.api.PlayReport
import com.fortu.player.api.PlaybackReport
import com.fortu.player.api.KIND_WEB
import com.fortu.player.api.DisconnectedException
import com.fortu.player.api.UnauthorizedException
import com.fortu.player.api.UpdateInfo
import com.fortu.player.api.UpdateStatusReport
import com.fortu.player.power.PowerPlan
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.JsonPrimitive
import java.io.File
import java.time.ZoneId

private const val TAG = "FortuPlayer"

private val json = kotlinx.serialization.json.Json { ignoreUnknownKeys = true }

/** Everything the UI can be showing. The pairing screen doubles as the error state. */
sealed interface PlayerState {
    data object Starting : PlayerState

    /** Unpaired, revoked, or 401'd — always lands here rather than on a black screen,
     *  because a screen showing a pairing code is diagnosable from across the room.
     *
     * `apiHost` matters when pairing "does not work": almost always the screen and the CMS are
     * talking to different servers. The pairing screen no longer shows it (it is Paskall's
     * front door, not a diagnostic page); the debug overlay does. */
    data class Pairing(
        val code: String,
        val apiHost: String,
        val error: String? = null,
        /** Counts polls, purely so the UI can show the wait is alive rather than frozen. */
        val checks: Int = 0,
    ) : PlayerState

    /** Claimed, shown briefly so the moment of success is visible rather than an abrupt cut. */
    data class Claimed(val deviceName: String) : PlayerState

    /** Fetching content before the first frame. Without this the screen sits on an idle card
     *  during a large download and looks broken rather than busy. */
    data class Preparing(
        val deviceName: String,
        /** Bytes landed so far across every file still to fetch, and the total — one bar that
         *  creeps up through a big video rather than jumping once per file. */
        val doneBytes: Long,
        val totalBytes: Long,
        val currentFile: String?,
        /** Measured over the last few seconds; null until there is enough to say. */
        val bytesPerSecond: Long?,
    ) : PlayerState

    /** Paired but nothing assigned. A valid state, not an error. */
    data class Idle(val deviceName: String) : PlayerState

    /** Paired, but the sync loop is failing — bad network, a server error, a manifest this
     *  build cannot read. Shown rather than left on the splash: a screen stuck on a logo is
     *  indistinguishable from a screen that has crashed, which is the whole failure this
     *  app's states exist to avoid. */
    data class Trouble(
        val deviceName: String?,
        val message: String,
        val apiHost: String,
        val attempts: Int,
    ) : PlayerState
    data class Playing(
        val slots: List<ManifestSlot>,
        val shuffle: Boolean,
        /** Bumped by the stall watchdog (see [PlayerEngine.restartIfStalled]) to make the UI
         *  rebuild its playback surface from scratch — the same content, a fresh loop. */
        val generation: Int = 0,
    ) : PlayerState {
        /** Every element across every slot, flattened — what most cache/count logic actually
         *  wants, since it does not care which slot an element belongs to. */
        val elements: List<ManifestElement> get() = slots.flatMap { it.elements }
    }
}

/** The real playback unit, regardless of which shape the backend actually answered with:
 *  prefers the real, multi-element [Manifest.slots], and falls back to treating each flat
 *  [Manifest.items] entry as its own single-element slot when a backend predates `slots`
 *  entirely (or this manifest genuinely has none). Every slot from here on is multi-element
 *  capable — nothing downstream needs to know which path built it. */
private fun Manifest.effectiveSlots(): List<ManifestSlot> {
    if (slots.isNotEmpty()) return slots
    return items.map { item ->
        ManifestSlot(
            id = item.id,
            durationSeconds = item.durationSeconds,
            elements = listOf(
                ManifestElement(
                    id = item.id,
                    mediaId = item.mediaId,
                    kind = item.kind,
                    url = item.url,
                    checksum = item.checksum,
                    bytes = item.bytes,
                    fit = item.fit,
                    hasAudio = item.hasAudio,
                ),
            ),
        )
    }
}

private fun MediaStore.isFullyCached(slot: ManifestSlot): Boolean = slot.elements.all { isCached(it) }


data class DebugInfo(
    val deviceName: String? = null,
    val version: String? = null,
    val cachedBytes: Long = 0,
    val itemCount: Int = 0,
    val lastPoll: String = "never",
    val lastError: String? = null,
    val apiBaseUrl: String = "",
    /** Whether Device Owner provisioning actually took — the one thing you cannot tell by
     *  looking at a screen, and the difference between a kiosk and a phone showing an app. */
    val kiosk: String = "unknown",
    /** Which schedule is overriding the default right now, if any. */
    val schedule: String? = null,
    /** Where the most recent self-update attempt (automatic or manually requested from the
     *  debug overlay) stands — "no update available", "installing 2.0.0…", a failure, or null
     *  before any check has happened yet. Separate from [lastError], which is sync/poll
     *  failures — conflating the two made a successful "up to date" read as an error. */
    val updateStatus: String? = null,
    /** The same thing, structured — what the on-screen banner (`ui/Screens.kt`'s
     *  `UpdateBanner`) draws while an install is under way or has just failed. Null when no
     *  update is in flight. */
    val update: UpdateProgress? = null,
    /** The video decoder in use, once one has been initialised. */
    val decoder: String? = null,
    /** Frames dropped since this process started — the on-screen counterpart of what each
     *  heartbeat reports as a delta. */
    val droppedFrames: Int = 0,
    /** Throughput of the last media download that was large enough to measure. */
    val downloadBytesPerSecond: Long? = null,
)

enum class UpdatePhase { DOWNLOADING, INSTALLING, FAILED }

/** Where an install stands, for the screen itself to show — mirrors what is reported to the
 *  CMS (see [PlayerEngine.reportUpdate]), so someone standing at the screen and someone at
 *  the CMS see the same story. */
data class UpdateProgress(
    val version: String,
    val phase: UpdatePhase,
    /** 0–100 while downloading, when the size is known. */
    val percent: Int? = null,
    val doneBytes: Long = 0,
    val totalBytes: Long? = null,
    /** The reason, when [phase] is FAILED. */
    val detail: String? = null,
    val atMillis: Long = 0,
)


/**
 * Download speed as a person expects to read it: bytes over the last few seconds, not since
 * the start (which drags for minutes after one slow patch) and not the last chunk (which
 * flickers). Samples are (bytes so far, when); the rate is taken across whatever the window
 * holds once it spans a second.
 */
class DownloadSpeed(private val clock: () -> Long, private val windowMillis: Long = 3_000L) {
    private val samples = ArrayDeque<Pair<Long, Long>>()

    fun record(bytesSoFar: Long, nowMillis: Long = clock()) {
        samples.addLast(bytesSoFar to nowMillis)
        while (samples.size > 1 && nowMillis - samples.first().second > windowMillis) samples.removeFirst()
    }

    fun bytesPerSecond(nowMillis: Long = clock()): Long? {
        val first = samples.firstOrNull() ?: return null
        val last = samples.last()
        val elapsed = last.second - first.second
        if (elapsed < 1_000L || last.first < first.first) return null
        return (last.first - first.first) * 1000 / elapsed
    }
}

/**
 * The player's whole state machine, with no Android dependencies.
 *
 * Extracted from `PlayerViewModel` so it can be driven on a plain JVM with fakes. The
 * ViewModel is now a thin shell that owns a coroutine scope and forwards state to Compose;
 * everything that can be wrong lives here, where a test can reach it.
 */
class PlayerEngine(
    private val api: PlayerApi,
    private val store: TokenStore,
    private val cache: MediaStore,
    private val appVersion: String,
    private val apiBaseUrl: String,
    /** Injected so tests can assert on it without a device-owner check. */
    private val canSelfUpdate: () -> Boolean = { false },
    /** Whether this app is Device Owner, reported on every heartbeat so the CMS can label the
     *  screen and explain what it can't do. Separate from [canSelfUpdate] because the two may
     *  one day differ (an assisted install needs no policy). */
    private val isDeviceOwner: () -> Boolean = { false },
    /** Downloads and hands the APK to the system, calling back with (bytes so far, total)
     *  as it goes — `kiosk/SelfUpdater`. Blocking; only ever called on [io]. */
    private val installUpdate: (UpdateInfo, (Long, Long?) -> Unit) -> InstallResult =
        { _, _ -> InstallResult.Failed("no installer") },
    /** Why the system rejected the install we last handed over, if it did — see
     *  `kiosk/UpdateResultReceiver`. `PackageInstaller` answers by broadcast long after
     *  [installUpdate] has returned, so without folding that verdict back in here a rejected
     *  update never starts the retry backoff and the screen re-downloads the same doomed APK
     *  on every heartbeat, forever. Null when there is nothing new to collect. Injected rather
     *  than read from `UpdateOutcome` directly, like everything else Android-shaped here. */
    private val consumeInstallFailure: () -> String? = { null },
    /** The real side effects of volume/brightness (`AudioManager`, `Settings.System`) live in
     *  `kiosk/DeviceSettingsApplier.kt`, not here — same reasoning as `installUpdate` above:
     *  this class has no Android dependencies, so anything that needs one is a callback. */
    private val applySettings: (ManifestSettings) -> Unit = {},
    /** Same reasoning, the other direction: what volume/brightness actually are right now,
     *  read from the system for the next heartbeat to report. */
    private val currentSettings: () -> Map<String, JsonPrimitive> = { emptyMap() },
    /** Sleeps or wakes the screen (`DeviceSettingsApplier.applyPower`). Called only when the
     *  power decision changes — see [evaluatePower]. */
    private val applyPower: (Boolean) -> Unit = {},
    /** Wall clock, injectable so the power schedule can be driven to a chosen moment in tests. */
    private val clock: () -> Long = System::currentTimeMillis,
    /** Primes whatever makes the *next* display of this file fast — Coil's memory cache for
     *  an image (so `AsyncImage` doesn't pay a decode cost the first time it's shown), the OS
     *  page cache for a video (there is no single "decode once" step for video the way there
     *  is for a bitmap, so priming the read is most of what separates a cold first play from
     *  a warm one). Called for everything about to go on screen, right before a changed
     *  manifest switches over — so the first loop through new content looks like every loop
     *  after it, not a cold start. A no-op default is harmless: display just decodes/buffers
     *  on first use, exactly like before this existed. */
    private val warmMedia: suspend (File, kind: String) -> Unit = { _, _ -> },
    /** Where blocking work runs. Injected so tests can supply the test scheduler's
     *  dispatcher — with a hard-coded `Dispatchers.IO` the download and state-transition work
     *  escapes virtual time entirely and assertions race it. */
    private val io: CoroutineDispatcher = Dispatchers.IO,
    /** Wakes the poll loop early when a push arrives (see backend/app/infra/mqtt.py).
     *  Defaults to [NoopPushClient] — nothing to connect to, nothing ever emitted — which is
     *  exactly "no push available" and leaves the loop on its plain poll cadence. */
    private val push: PushClient = NoopPushClient,
) {
    private val _state = MutableStateFlow<PlayerState>(PlayerState.Starting)
    val state = _state.asStateFlow()

    private val _debug = MutableStateFlow(DebugInfo(apiBaseUrl = apiBaseUrl))
    val debug = _debug.asStateFlow()

    /** Exposed separately from [DebugInfo] because the exit-PIN dialog needs to read
     *  `appPassword` directly — that one is compared by the UI, not applied as a side
     *  effect, so it has nowhere else to live. */
    private val _settings = MutableStateFlow(ManifestSettings())
    val settings = _settings.asStateFlow()

    /** The orientation the CMS has configured, published the moment a manifest is adopted.
     *  Deliberately not carried on [PlayerState]: state is emitted at the *end* of the content
     *  pipeline, so a rotation used to wait behind downloading and warming every element —
     *  on a screen carrying a large video, long enough to look broken. Rotating is a property
     *  of the screen, not of what happens to be playing on it.
     */
    private val _orientation = MutableStateFlow<String?>(null)
    val orientation = _orientation.asStateFlow()

    private var screenWidth = 0
    private var screenHeight = 0

    /** The offer a self-update last failed for (see [offerKey]), and when — so a failure backs
     *  off instead of re-downloading the APK on every 30-second heartbeat forever, but still
     *  gets retried after [UPDATE_RETRY_COOLDOWN_MILLIS] rather than silently giving up until
     *  someone physically restarts the screen. A *different* offer — a newer rollout, a
     *  rollback, or the same version re-issued from the CMS as "Retry now" — is always
     *  attempted immediately, cooldown or not. */
    private var lastFailedUpdate: Pair<String, Long>? = null

    /** The offer handed to the installer and not yet ruled on. Held because the rejection
     *  that comes back by broadcast doesn't name a version, and [lastFailedUpdate] is keyed
     *  by one. */
    private var pendingUpdate: UpdateInfo? = null

    /** The version this screen has already told the CMS it cannot install (not Device Owner).
     *  Once per version, not once per heartbeat: the offer comes back on every one. */
    private var reportedUnsupportedFor: String? = null

    /** When the current schedule window ends, as epoch millis. The poll interval is
     *  shortened to land on it. */
    private var validUntilMillis: Long? = null

    /** Plays observed since the last heartbeat, drained when one is sent.
     *  Bounded so a screen that cannot reach the server for hours accumulates a report
     *  instead of unbounded memory — the oldest entries are the ones worth dropping. */
    private val pendingPlays = java.util.Collections.synchronizedList(mutableListOf<PlayReport>())

    /** Errors observed since the last heartbeat, reported the same way. */
    private val pendingErrors = java.util.Collections.synchronizedList(mutableListOf<String>())

    /** When the playback surface last said a slot finished (or playback last (re)started) —
     *  what the stall watchdog compares against. See [restartIfStalled]. */
    @Volatile private var lastPlayAt = 0L
    private var playbackGeneration = 0

    /** Dropped video frames since the last heartbeat, and the decoder that dropped them —
     *  see [reportVideoStats]. */
    private val droppedSinceBeat = java.util.concurrent.atomic.AtomicInteger(0)
    @Volatile private var decoderName: String? = null
    /** Bytes per second over the last media download large enough to say something. */
    @Volatile private var lastDownloadBps: Long? = null

    fun setScreenSize(w: Int, h: Int) { screenWidth = w; screenHeight = h }

    fun setKioskState(description: String) {
        _debug.update { it.copy(kiosk = description) }
    }

    suspend fun run() = coroutineScope {
        // Alongside the sync loop, not inside it: a scheduled power change has to happen on
        // time even when polling is failing or the network is gone entirely.
        launch { runPowerLoop() }
        runForever()
    }

    private suspend fun runForever() {
        val host = apiBaseUrl.substringAfter("://").substringBefore("/")
        var consecutiveFailures = 0
        var unauthorizedStreak = 0

        while (true) {
            try {
                val token = store.token() ?: pairUntilClaimed() ?: continue
                // Idempotent — see PushClient. Called every time through the loop rather than
                // only once so a screen paired by an older build (no saved device id yet)
                // starts pushing the moment it re-pairs, with nothing else to trigger it.
                store.deviceId()?.let { push.connect(it, store.mqttPassword() ?: "") }
                syncAndPlay(token)
                consecutiveFailures = 0
                unauthorizedStreak = 0
            } catch (e: DisconnectedException) {
                // Deliberate and final, unlike a 401 — no streak to confirm. Whoever clicked
                // Disconnect is watching for the pairing code to come back.
                Log.w(TAG, "disconnected by the CMS — resetting and re-pairing")
                resetForNewOwner()
                consecutiveFailures = 0
                unauthorizedStreak = 0
            } catch (e: UnauthorizedException) {
                // Discarding the token is destructive and irreversible *from the device*:
                // somebody has to physically walk to the screen and re-pair it. A single 401
                // is not enough evidence to do that — a request landing mid-deploy, a proxy
                // hiccup or a brief server fault would permanently unpair a working screen.
                //
                // So require several in a row — but confirm or dismiss the suspicion quickly
                // rather than on the normal 30s poll cadence. An admin who just unpaired or
                // deleted a screen is watching it, and a genuine revocation answers 401 just
                // as reliably five seconds from now as it will in thirty; there is nothing to
                // wait for. A transient one still costs nothing and is forgotten on success.
                unauthorizedStreak++
                Log.w(TAG, "token rejected ($unauthorizedStreak/$UNAUTHORIZED_BEFORE_REPAIR)")
                if (unauthorizedStreak >= UNAUTHORIZED_BEFORE_REPAIR) {
                    Log.w(TAG, "token rejected repeatedly — clearing and re-pairing")
                    store.clear()
                    push.disconnect()
                    forgetAccountSettings()
                    unauthorizedStreak = 0
                    consecutiveFailures = 0
                    _state.value = PlayerState.Starting
                } else {
                    val current = _state.value
                    if (current !is PlayerState.Playing) {
                        _state.value = PlayerState.Trouble(
                            deviceName = store.name(),
                            message = "Server rejected this screen's credential " +
                                "($unauthorizedStreak of $UNAUTHORIZED_BEFORE_REPAIR)",
                            apiHost = host,
                            attempts = unauthorizedStreak,
                        )
                    }
                    delay(UNAUTHORIZED_RETRY_SECONDS * 1000L)
                }
            } catch (e: Exception) {
                Log.e(TAG, "loop error", e)
                consecutiveFailures++
                _debug.update { it.copy(lastError = e.message) }

                // Only take over the screen once something is playing is not an option. A
                // single failed poll while content is on screen must not replace it with an
                // error card — the cached loop is still the best thing to be showing.
                val current = _state.value
                val isShowingContent = current is PlayerState.Playing
                if (!isShowingContent) {
                    _state.value = PlayerState.Trouble(
                        deviceName = store.name(),
                        message = e.message ?: e::class.simpleName ?: "Unknown error",
                        apiHost = host,
                        attempts = consecutiveFailures,
                    )
                }
                delay(POLL_SECONDS * 1000L)
            }
        }
    }

    /** Shows a code and polls until a human claims it. Returns the new device token. */
    private suspend fun pairUntilClaimed(): String? {
        val host = apiBaseUrl.substringAfter("://").substringBefore("/")

        val pair = try {
            api.startPairing()
        } catch (e: Exception) {
            // No network yet: say so on screen instead of showing a code that cannot work.
            _state.value = PlayerState.Pairing(
                code = "······",
                apiHost = host,
                error = "Cannot reach the server. Check this screen's network.",
            )
            delay(5_000)
            return null
        }

        var checks = 0
        _state.value = PlayerState.Pairing(pair.pairingCode, host, checks = checks)

        while (true) {
            delay(pair.pollSeconds * 1000L)
            checks++
            val poll = try {
                api.pollPairing(pair.pollToken)
            } catch (e: Exception) {
                _debug.update { it.copy(lastError = e.message) }
                _state.value = PlayerState.Pairing(
                    pair.pairingCode, host,
                    error = "Lost connection — retrying",
                    checks = checks,
                )
                continue
            }
            // 404 → the code expired. Start over with a fresh one rather than showing a
            // stale code nobody can claim.
            if (poll == null) return null

            val token = poll.deviceToken
            if (poll.claimed && token != null) {
                store.saveToken(token, poll.name)
                store.saveDeviceId(poll.deviceId)
                poll.mqttPassword?.let { store.saveMqttPassword(it) }
                _debug.update { it.copy(deviceName = poll.name) }
                // Held briefly so pairing visibly succeeds instead of cutting to black.
                _state.value = PlayerState.Claimed(poll.name ?: "This screen")
                delay(1_500)
                return token
            }

            _state.value = PlayerState.Pairing(pair.pairingCode, host, checks = checks)
        }
    }

    /** The steady state: poll, download what changed, play, heartbeat. */
    private suspend fun syncAndPlay(token: String) {
        var beatsSincePoll = 0

        // Play whatever was on screen before the restart, from disk, before touching the
        // network. A screen that comes back from a power cut with the router still booting
        // must show content, not a logo — the files are already cached, and this is the
        // only thing that knows which of them to play.
        restoreFromDisk()

        while (true) {
            // Only send an ETag when there is something on screen for a 304 to mean. After a
            // restart with nothing restored, "nothing changed" is the one answer the player
            // cannot act on: the server is right, and the screen still has nothing to show.
            val etag = if (_state.value is PlayerState.Playing || _state.value is PlayerState.Idle) {
                store.etag()
            } else {
                null
            }
            val manifest = api.fetchManifest(token, etag)

            _debug.update { it.copy(lastPoll = "just now", lastError = null) }

            if (manifest != null) {
                applyManifest(manifest)
                store.saveEtag("\"${manifest.version}\"")
                runCatching { store.saveManifestJson(json.encodeToString(Manifest.serializer(), manifest)) }
                    .onFailure { Log.w(TAG, "could not persist manifest", it) }
            }

            // Heartbeat carries liveness and reported resolution. Its response includes the
            // current version, so a screen beating more often than it polls learns early
            // that it should re-fetch.
            try {
                // Drained before the call, not after: if the request fails these are lost
                // rather than resent forever. Proof-of-play is a best-effort record, and a
                // screen retrying a growing backlog on every beat would be worse than a gap.
                val plays = synchronized(pendingPlays) {
                    pendingPlays.toList().also { pendingPlays.clear() }
                }
                val errors = synchronized(pendingErrors) {
                    pendingErrors.toList().also { pendingErrors.clear() }
                }

                val res = api.heartbeat(
                    token,
                    HeartbeatRequest(
                        appVersion = appVersion,
                        screen = if (screenWidth > 0) HeartbeatScreen(screenWidth, screenHeight) else null,
                        currentItemId = null,
                        errors = errors,
                        plays = plays,
                        reportedSettings = currentSettings().ifEmpty { null },
                        playback = PlaybackReport(
                            droppedFrames = droppedSinceBeat.getAndSet(0),
                            decoder = decoderName,
                            downloadBytesPerSecond = lastDownloadBps,
                        ),
                        deviceOwner = isDeviceOwner(),
                    ),
                )
                res.update?.let { maybeSelfUpdate(token, it) }
                restartIfStalled()

                if (etag != null && "\"${res.version}\"" != etag) {
                    // Version moved under us — loop again soon rather than waiting a full
                    // poll. Never with zero delay, though: a version that keeps disagreeing
                    // on every single heartbeat (a stuck race, a server bug) must not turn
                    // into a busy loop hammering the CMS with no backoff at all.
                    delay(MIN_POLL_MILLIS)
                    continue
                }
            } catch (e: UnauthorizedException) {
                throw e
            } catch (e: DisconnectedException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "heartbeat failed (continuing)", e)
            }

            beatsSincePoll++
            waitForNextPoll(nextPollDelayMillis())
        }
    }

    /**
     * Sleeps for [ms] — unless [push] wakes it first.
     *
     * A plain `delay(ms)` would ignore a push entirely; racing it against [PushClient.signal]
     * means a screen with a live push connection polls again the moment the CMS actually
     * changes something, while a screen with none (push disabled, MQTT unreachable, an older
     * pairing with no device id) behaves exactly as it always has — this is strictly additive.
     */
    private suspend fun waitForNextPoll(ms: Long) {
        withTimeoutOrNull(ms) { push.signal.first() }
    }

    /**
     * Normally the fixed poll interval — but never sleep past a schedule boundary.
     *
     * Without this a daypart change lands up to a full poll late: a breakfast menu still on
     * screen half a minute after it should have switched. Clamped to a floor so a boundary
     * in the past (clock skew, a long download) cannot spin the loop.
     */
    private fun nextPollDelayMillis(): Long {
        val normal = POLL_SECONDS * 1000L
        val boundary = validUntilMillis ?: return normal
        val untilBoundary = boundary - System.currentTimeMillis()
        return when {
            untilBoundary <= 0 -> MIN_POLL_MILLIS
            untilBoundary < normal -> maxOf(untilBoundary, MIN_POLL_MILLIS)
            else -> normal
        }
    }

    /** The screen's timezone per the CMS — the power schedule is evaluated on it. */
    @Volatile private var deviceTimezone: String? = null

    /** What [applyPower] was last called with, so a decision is applied once per change rather
     *  than on every check — a screen woken by hand during scheduled off hours stays on until
     *  the next change instead of being put straight back to sleep. Null in a fresh process, so
     *  the first decision after a reboot always applies. */
    private var lastAppliedPower: Boolean? = null

    /**
     * Everything this screen holds on behalf of the account that just let it go, gone — so the
     * next person to pair it starts from a screen that could be fresh out of the box: no token,
     * no cached content of someone else's, awake, touch unlocked, no exit PIN, no power
     * schedule, orientation back to the hardware's own until a new manifest says otherwise, and
     * nothing queued to report to an account that no longer owns it.
     */
    private suspend fun resetForNewOwner() {
        store.clear()
        push.disconnect()
        forgetAccountSettings()
        runCatching { cache.evictExcept(emptyList()) }
            .onFailure { Log.w(TAG, "could not clear cached content on disconnect", it) }
        synchronized(pendingPlays) { pendingPlays.clear() }
        synchronized(pendingErrors) { pendingErrors.clear() }
        pendingUpdate = null
        lastFailedUpdate = null
        reportedUnsupportedFor = null
        validUntilMillis = null
        droppedSinceBeat.set(0)
        lastDownloadBps = null
        _orientation.value = null
        _debug.update {
            DebugInfo(apiBaseUrl = it.apiBaseUrl, kiosk = it.kiosk)
        }
        _state.value = PlayerState.Starting
    }

    /**
     * A screen that has lost its account — deleted or unpaired in the CMS — must stop acting on
     * that account's settings: no exit PIN, touch unlocked, no power schedule or override, and
     * awake. Storage is already wiped by `store.clear()`; this clears what the running process
     * still holds, which would otherwise keep the old PIN, touch lock and power plan alive until
     * the app restarts. Pairing again delivers whatever settings the screen should have from then
     * on.
     */
    private fun forgetAccountSettings() {
        _settings.value = ManifestSettings()
        deviceTimezone = null
        synchronized(this) {
            if (lastAppliedPower == false) {
                runCatching { applyPower(true) }.onFailure { Log.w(TAG, "wake after reset failed", it) }
            }
            lastAppliedPower = null
        }
    }

    private fun adoptSettings(manifest: Manifest) {
        deviceTimezone = manifest.device.timezone
        // Degrees when the backend sends them; the old portrait/landscape word otherwise. The
        // UI maps either (MainActivity), so a player and a backend can be updated in any order.
        _orientation.value = manifest.device.rotation?.toString() ?: manifest.device.orientation
        _settings.value = manifest.settings
        applySettings(manifest.settings)
        // Straight away, not on the next power check: a "Turn off now" should land with the
        // manifest that carries it.
        evaluatePower()
    }

    private suspend fun runPowerLoop() {
        while (true) delay(evaluatePower())
    }

    /**
     * Applies the current power decision (`power/PowerPlan.kt`) if it differs from what was last
     * applied, and returns how long to wait before checking again — the next known change if
     * that's sooner than the regular check, so a scheduled switch lands on the minute.
     */
    @Synchronized
    internal fun evaluatePower(): Long {
        val settings = _settings.value
        val zone = deviceTimezone?.let { runCatching { ZoneId.of(it) }.getOrNull() } ?: ZoneId.systemDefault()
        val now = clock()
        val decision = PowerPlan.decide(settings.powerSchedule, settings.powerOverride, now, zone)
        // No decision means nothing is configured — but a screen this process put to sleep must
        // not stay asleep just because the thing that said "off" is gone ("Resume schedule" with
        // no schedule clears the override entirely, and then nothing would ever say "on").
        val on = decision?.on ?: if (lastAppliedPower == false) true else null
        if (on != null && on != lastAppliedPower) {
            Log.i(TAG, "power ${if (on) "on" else "off"} (${decision?.source ?: "cleared"})")
            runCatching { applyPower(on) }.onFailure { Log.w(TAG, "power apply failed", it) }
            lastAppliedPower = on
        }
        val untilChange = decision?.nextChangeMillis?.let { it - now }
        return when {
            untilChange == null -> POWER_CHECK_MILLIS
            untilChange <= 0 -> MIN_POLL_MILLIS
            else -> minOf(untilChange, POWER_CHECK_MILLIS)
        }
    }

    private fun parseInstantMillis(iso: String?): Long? = try {
        if (iso == null) null
        else java.time.Instant.parse(iso.replace("+00:00", "Z")).toEpochMilli()
    } catch (e: Exception) {
        Log.w(TAG, "unparseable valid_until: $iso")
        null
    }

    /**
     * Restore the last known manifest from disk and play anything already cached.
     *
     * Deliberately does not download: this runs before the first network call, and its whole
     * purpose is getting pixels on screen while the network is still coming up — or never
     * does. Anything missing is filled in by the normal sync a moment later.
     */
    private suspend fun restoreFromDisk() {
        if (_state.value is PlayerState.Playing) return
        val stored = store.manifestJson() ?: return
        val manifest = runCatching { json.decodeFromString(Manifest.serializer(), stored) }
            .getOrElse {
                // A manifest written by an older build that this one cannot read. Not fatal:
                // drop it and let the normal fetch repopulate.
                Log.w(TAG, "stored manifest unreadable, ignoring", it)
                return
            }

        val playable = manifest.effectiveSlots().filter { cache.isFullyCached(it) }
        if (playable.isEmpty()) return

        Log.i(TAG, "restored ${playable.size} cached slots from disk")
        lastPlayAt = clock()
        _state.value = PlayerState.Playing(
            playable,
            manifest.playlist?.shuffle ?: false,
            playbackGeneration,
        )
        _debug.update {
            it.copy(deviceName = manifest.device.name, version = manifest.version,
                    itemCount = playable.size, schedule = manifest.scheduleName)
        }
        // Re-applied on the disk-restore path too, not just after a live poll: a screen
        // rebooting must come back at its configured volume/brightness immediately, not sit
        // at system defaults until the first network round trip lands.
        adoptSettings(manifest)
    }

    private suspend fun applyManifest(manifest: Manifest) = withContext(io) {
        validUntilMillis = parseInstantMillis(manifest.validUntil)
        adoptSettings(manifest)

        val slots = manifest.effectiveSlots()
        _debug.update {
            it.copy(
                deviceName = manifest.device.name,
                version = manifest.version,
                itemCount = slots.sumOf { slot -> slot.elements.size },
                schedule = manifest.scheduleName,
            )
        }

        if (slots.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name)
            cache.evictExcept(emptyList())
            _debug.update { it.copy(cachedBytes = cache.cachedBytes()) }
            return@withContext
        }

        // Download everything missing BEFORE switching the playlist, so a screen never shows
        // a gap while a file is still arriving. Flattened across every slot's elements — a
        // multi-element slot is not ready until every layer in it is.
        val allElements = slots.flatMap { it.elements }
        val missing = allElements.filter { !cache.isCached(it) }
        // One bar for the whole job, in bytes: a 40 MB video and a 40 KB logo are not two equal
        // steps, and a bar that moves within a file is what says "still going" on slow wifi.
        val totalBytes = missing.sumOf { it.bytes }.coerceAtLeast(0)
        val speed = DownloadSpeed(clock)
        var completedBytes = 0L
        var lastShownAt = 0L
        fun showPreparing(current: ManifestElement?, inFlight: Long, force: Boolean = false) {
            val now = clock()
            // Progress arrives per 64 KB chunk; the screen doesn't need every one of them.
            if (!force && now - lastShownAt < PREPARING_REFRESH_MILLIS) return
            lastShownAt = now
            _state.value = PlayerState.Preparing(
                manifest.device.name,
                doneBytes = (completedBytes + inFlight).coerceAtMost(totalBytes),
                totalBytes = totalBytes,
                currentFile = current?.let { "${it.kind} · ${it.bytes / 1_048_576} MB" },
                bytesPerSecond = speed.bytesPerSecond(now),
            )
        }
        // Only announce preparing when there is genuinely something to fetch — a routine poll
        // that changes nothing must not flash a progress screen over content that is playing.
        if (missing.isNotEmpty()) showPreparing(null, 0, force = true)

        for (element in allElements) {
            if (!cache.isCached(element)) {
                Log.i(TAG, "downloading ${element.checksum} (${element.bytes} bytes)")
                showPreparing(element, 0, force = true)
                try {
                    val startedAt = clock()
                    cache.download(element) { got ->
                        speed.record(completedBytes + got, clock())
                        showPreparing(element, got)
                    }
                    noteDownload(element.bytes, clock() - startedAt)
                } catch (e: Exception) {
                    Log.e(TAG, "download failed for ${element.id}", e)
                    _debug.update { it.copy(lastError = "download: ${e.message}") }
                    // Keep going: one bad element should not stop the rest of the loop from
                    // updating. The player skips any slot still missing one.
                }
                completedBytes += element.bytes
                speed.record(completedBytes, clock())
                showPreparing(element, 0, force = true)
            }
        }

        val playable = slots.filter { cache.isFullyCached(it) }

        // Warm everything that is actually about to go on screen before switching the
        // playlist over — so the first loop through this (new or changed) content looks like
        // every loop after it, not a cold start. `distinctBy` skips re-warming the same file
        // twice when one image or video is reused across several slots. Only updates the
        // Preparing screen if downloading already put it up; if nothing needed fetching,
        // whatever was already on screen just keeps looping a little longer instead of
        // flashing a progress screen over content that is playing fine.
        // A website has no file to warm — it loads live when its slot comes up.
        val toWarm = playable.flatMap { it.elements }.filter { it.kind != KIND_WEB }.distinctBy { it.checksum }
        for (element in toWarm) {
            if (missing.isNotEmpty()) {
                _state.value = PlayerState.Preparing(
                    manifest.device.name, totalBytes, totalBytes,
                    "getting ${element.kind} ready", null,
                )
            }
            runCatching { warmMedia(cache.fileFor(element), element.kind) }
                .onFailure { Log.w(TAG, "warm-up failed for ${element.id}", it) }
        }

        if (playable.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name)
        } else {
            lastPlayAt = clock()
            _state.value = PlayerState.Playing(
                playable,
                manifest.playlist?.shuffle ?: false,
                playbackGeneration,
            )
        }

        // Evict only after the new set is safely on disk.
        cache.evictExcept(allElements.filter { it.kind != KIND_WEB }.map { it.checksum })
        _debug.update { it.copy(cachedBytes = cache.cachedBytes()) }
    }

    /**
     * Install a published build over ourselves — called both off the regular heartbeat
     * (cooldown-gated, see [maybeSelfUpdate]) and from [checkForUpdateNow] (a human standing
     * at the screen, who does not want to hear "try again in ten minutes").
     *
     * Everything that happens is said twice: to the screen (the banner, the debug overlay) and
     * to the CMS ([reportUpdate]) — the two places someone might be looking, neither of which
     * could previously tell a download crawling over bad wifi from one that had failed an
     * hour ago. Progress reports to the CMS are throttled; the screen sees every byte.
     */
    private fun performInstall(token: String, update: UpdateInfo) {
        Log.i(TAG, "installing update ${update.version}")
        pendingUpdate = update
        lastFailedUpdate = null
        setUpdateProgress(UpdateProgress(update.version, UpdatePhase.DOWNLOADING, percent = 0, totalBytes = update.bytes, atMillis = clock()))
        reportUpdate(token, update.version, "downloading", 0, null)

        var lastReportedPct = 0
        var lastReportAt = clock()
        val result = installUpdate(update) { done, total ->
            val pct = total?.takeIf { it > 0 }?.let { ((done * 100) / it).toInt().coerceIn(0, 100) }
            setUpdateProgress(UpdateProgress(update.version, UpdatePhase.DOWNLOADING, pct, done, total, atMillis = clock()))
            // Every few percent or every few seconds, whichever comes first — enough for a
            // moving number on the CMS, and for its "no news for a while" check to stay
            // quiet as long as bytes are still arriving, however slowly.
            val now = clock()
            if (pct != null && (pct - lastReportedPct >= UPDATE_REPORT_STEP_PCT || now - lastReportAt >= UPDATE_REPORT_INTERVAL_MILLIS)) {
                lastReportedPct = pct
                lastReportAt = now
                reportUpdate(token, update.version, "downloading", pct, null)
            }
        }
        when (result) {
            // Handed over, not landed: whether it installs is answered later, by broadcast.
            // Claiming "installed" at this point is what made a rejected update look like one
            // still in progress.
            InstallResult.HandedOver -> {
                setUpdateProgress(UpdateProgress(update.version, UpdatePhase.INSTALLING, 100, atMillis = clock()))
                reportUpdate(token, update.version, "installing", 100, null)
            }
            is InstallResult.Failed -> {
                pendingUpdate = null
                lastFailedUpdate = offerKey(update) to clock()
                setUpdateProgress(UpdateProgress(update.version, UpdatePhase.FAILED, detail = result.reason, atMillis = clock()))
                reportUpdate(token, update.version, "failed", null, result.reason)
            }
        }
    }

    /** Called off every heartbeat response. Backs off a failed offer for
     *  [UPDATE_RETRY_COOLDOWN_MILLIS] instead of hammering the same failing download — see
     *  [checkForUpdateNow] for the version a person can trigger on demand, which skips this. */
    private fun maybeSelfUpdate(token: String, update: UpdateInfo) {
        // Collect the installer's verdict on the *previous* hand-off before deciding anything:
        // it arrives by broadcast, long after the call that started that install returned, so
        // this is one of the two moments the engine can learn the attempt actually failed
        // (the other is [onInstallVerdict], which does not wait for a heartbeat).
        collectInstallVerdict(token)

        if (!canSelfUpdate()) {
            Log.i(TAG, "update ${update.version} available but this device cannot install silently")
            // Not a failure worth a banner on screen — a sideloaded or development install
            // simply updates by hand — but very much one worth telling the CMS, where "pending
            // forever" and "will never happen" otherwise look the same.
            if (reportedUnsupportedFor != update.version) {
                reportedUnsupportedFor = update.version
                _debug.update { it.copy(updateStatus = "${update.version} available, but this screen can't self-install") }
                reportUpdate(token, update.version, "failed", null, NOT_DEVICE_OWNER_REASON)
            }
            return
        }
        val lastFailure = lastFailedUpdate
        if (lastFailure != null && lastFailure.first == offerKey(update) &&
            clock() - lastFailure.second < UPDATE_RETRY_COOLDOWN_MILLIS
        ) {
            // Say so rather than returning in silence: from the screen, a backed-off retry and
            // an update that is doing nothing at all look identical.
            val waitSeconds =
                (UPDATE_RETRY_COOLDOWN_MILLIS - (clock() - lastFailure.second)) / 1000
            _debug.update {
                it.copy(updateStatus = "update ${update.version} failed — retrying in ${waitSeconds}s")
            }
            return
        }
        performInstall(token, update)
    }

    /**
     * "Check for update" from the debug overlay's long-press menu — the on-screen counterpart
     * to rolling an update out from the CMS. Sends its own heartbeat rather than waiting for
     * the next scheduled one, and — unlike [maybeSelfUpdate] — ignores any cooldown from a
     * previous failed attempt: someone standing at the screen asking for this explicitly is
     * exactly the moment a ten-minute backoff should not apply.
     *
     * Safe to call while the normal poll loop is also running: heartbeats are side-effect-safe
     * to send more than once, and the pending-plays/errors queues it drains from are already
     * synchronized against exactly this kind of concurrent access.
     */
    suspend fun checkForUpdateNow() {
        _debug.update { it.copy(updateStatus = "checking for update…") }
        val token = store.token()
        if (token == null) {
            _debug.update { it.copy(updateStatus = "not paired yet") }
            return
        }
        try {
            // The whole thing — heartbeat and, if there's an update, the download+install —
            // is blocking I/O, moved off whatever dispatcher the caller (the UI) is on. The
            // automatic path gets this for free by living inside `syncAndPlay`, which only
            // ever runs on `io` to begin with.
            withContext(io) {
                val res = api.heartbeat(
                    token,
                    HeartbeatRequest(
                        appVersion = appVersion,
                        screen = if (screenWidth > 0) HeartbeatScreen(screenWidth, screenHeight) else null,
                        deviceOwner = isDeviceOwner(),
                    ),
                )
                val update = res.update
                when {
                    update == null ->
                        _debug.update { it.copy(updateStatus = "up to date ($appVersion)") }
                    !canSelfUpdate() ->
                        _debug.update {
                            it.copy(updateStatus = "${update.version} available, but this screen can't self-install")
                        }
                    else -> performInstall(token, update)
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "manual update check failed", e)
            _debug.update { it.copy(updateStatus = "check failed: ${e.message}") }
        }
    }

    /**
     * The installer has just ruled on the last hand-off (`UpdateOutcome.failures` fired). Acts
     * on it now — backoff, banner, and the reason sent to the CMS — instead of at the next
     * heartbeat, which could be most of a poll interval away with the CMS saying "installing"
     * the whole time. Idempotent with the heartbeat path: whichever collects the verdict first
     * gets it, the other finds nothing.
     */
    suspend fun onInstallVerdict() {
        val token = store.token() ?: return
        withContext(io) { collectInstallVerdict(token) }
    }

    private fun collectInstallVerdict(token: String) {
        val reason = consumeInstallFailure() ?: return
        val rejected = pendingUpdate ?: return
        pendingUpdate = null
        lastFailedUpdate = offerKey(rejected) to clock()
        setUpdateProgress(UpdateProgress(rejected.version, UpdatePhase.FAILED, detail = reason, atMillis = clock()))
        reportUpdate(token, rejected.version, "failed", null, reason)
    }

    /** Version plus when it was offered: the same version offered again later (the CMS's
     *  "Retry now" re-issues the pin with a fresh time) is a new offer, not a repeat. An older
     *  server sends no time, which degrades to keying on version alone — exactly as before. */
    private fun offerKey(update: UpdateInfo) = "${update.version}@${update.requestedAt ?: ""}"

    private fun setUpdateProgress(progress: UpdateProgress) {
        val text = when (progress.phase) {
            UpdatePhase.DOWNLOADING ->
                "downloading ${progress.version}" + (progress.percent?.let { " · $it%" } ?: "…")
            UpdatePhase.INSTALLING -> "installing update ${progress.version}…"
            UpdatePhase.FAILED -> "update ${progress.version} failed — ${progress.detail}"
        }
        _debug.update { it.copy(update = progress, updateStatus = text) }
    }

    /** Best effort, never fatal: the update must not be able to fail because a report about it
     *  couldn't be sent, and the next report supersedes a lost one anyway. Blocking; only ever
     *  called from [io]. */
    private fun reportUpdate(token: String, version: String, state: String, pct: Int?, detail: String?) {
        try {
            api.reportUpdateStatus(token, UpdateStatusReport(version, state, pct, detail))
        } catch (e: Exception) {
            Log.w(TAG, "update status report ($state) not delivered: ${e.message}")
        }
    }

    /** Called by the playback surface each time a slot finishes — once per element it
     *  contained, all sharing the same timing, since every element in a slot is on screen for
     *  exactly the same window. */
    fun reportPlay(slot: ManifestSlot, startedAtMillis: Long, seconds: Int) {
        lastPlayAt = clock()
        synchronized(pendingPlays) {
            for (element in slot.elements) {
                if (pendingPlays.size >= MAX_PENDING_PLAYS) pendingPlays.removeAt(0)
                pendingPlays.add(
                    PlayReport(
                        // Null against an older backend that does not send it. The server then
                        // falls back to whatever filename it can resolve, and the play is still
                        // recorded rather than dropped.
                        mediaId = element.mediaId,
                        // Left blank on purpose: the server resolves the real name from
                        // mediaId, so the log cannot drift when a file is renamed. A website
                        // has no media id, so its address is the name.
                        filename = if (element.kind == KIND_WEB) element.url else "",
                        startedAt = java.time.Instant.ofEpochMilli(startedAtMillis).toString(),
                        seconds = seconds,
                    )
                )
            }
        }
    }

    /**
     * The watchdog for the loop itself. A multi-slot playlist reports a play every time a slot
     * finishes; if none has been reported for far longer than any slot could last, the loop has
     * stopped advancing while the app is otherwise alive — a screen showing the same picture
     * for an hour, heartbeating as if nothing were wrong. Seen on a real box with a two-second
     * picture loop. Whatever the cause, the recovery is the same: bump [PlayerState.Playing]'s
     * generation, which makes the UI rebuild its playback surface from scratch with the same
     * content — and say so to the CMS, so it is at least counted.
     *
     * Checked off the poll loop, so at most once per poll interval. A one-slot playlist reports
     * on its own timer, and a single-video slot may legitimately run to the watchdog cap, so
     * the threshold is the longest slot or that cap, plus a generous grace.
     */
    internal fun restartIfStalled() {
        val playing = _state.value as? PlayerState.Playing ?: return
        if (playing.slots.isEmpty()) return
        val longestSlotMillis = playing.slots.maxOf { it.durationSeconds } * 1000L
        val threshold = maxOf(longestSlotMillis, SINGLE_VIDEO_CAP_MILLIS) + STALL_GRACE_MILLIS
        val silentFor = clock() - lastPlayAt
        if (silentFor < threshold) return
        Log.w(TAG, "playback stalled — no slot finished for ${silentFor / 1000}s; restarting the surface")
        reportError("playback stalled for ${silentFor / 1000}s — restarted the loop")
        playbackGeneration++
        lastPlayAt = clock()
        _state.value = playing.copy(generation = playbackGeneration)
    }

    /**
     * From the playback surface's ExoPlayer analytics: frames the decoder dropped (as it
     * reports them, in batches), and which decoder it picked. Batched onto the next heartbeat
     * as a delta; shown on the debug overlay as a running total. The numbers behind "is this
     * box coping?", so tuning is done on evidence rather than by watching a wall.
     */
    fun reportVideoStats(droppedFrames: Int, decoder: String?) {
        if (droppedFrames > 0) droppedSinceBeat.addAndGet(droppedFrames)
        if (decoder != null) decoderName = decoder
        _debug.update {
            it.copy(decoder = decoderName, droppedFrames = it.droppedFrames + droppedFrames.coerceAtLeast(0))
        }
    }

    /** A download's throughput, kept only when the file was big and slow enough to measure —
     *  a 40 KB thumbnail in 30 ms says nothing about the link. */
    private fun noteDownload(bytes: Long, elapsedMillis: Long) {
        if (bytes < MIN_MEASURED_DOWNLOAD_BYTES || elapsedMillis < MIN_MEASURED_DOWNLOAD_MILLIS) return
        val bps = bytes * 1000 / elapsedMillis
        lastDownloadBps = bps
        _debug.update { it.copy(downloadBytesPerSecond = bps) }
    }

    fun reportError(message: String) {
        synchronized(pendingErrors) {
            if (pendingErrors.size >= MAX_PENDING_ERRORS) pendingErrors.removeAt(0)
            pendingErrors.add(message.take(500))
        }
        _debug.update { it.copy(lastError = message) }
    }


    companion object {
        const val POLL_SECONDS = 30

        /** Never poll faster than this, whatever a boundary says. */
        const val MIN_POLL_MILLIS = 2_000L
        /** How often power is re-checked when no change is due sooner — also the most a
         *  missed or skewed wake-up can leave a screen in the wrong state. */
        const val POWER_CHECK_MILLIS = 30_000L

        /** How long a failed self-update backs off before retrying the *same* version — long
         *  enough that a persistent failure (bad wifi, a bad build) doesn't re-download the
         *  APK on every 30-second heartbeat forever, short enough that a transient failure
         *  recovers on its own well within a support call. */
        const val UPDATE_RETRY_COOLDOWN_MILLIS = 10 * 60 * 1000L

        /** How often download progress is sent to the CMS — see [performInstall]. */
        const val UPDATE_REPORT_STEP_PCT = 5
        const val UPDATE_REPORT_INTERVAL_MILLIS = 3_000L

        /** Said once per offered version, so the CMS can tell "can't" from "hasn't yet". Kept
         *  here rather than in `kiosk/SelfUpdater` so the JVM tests can assert on it. */
        const val NOT_DEVICE_OWNER_REASON =
            "this screen isn't provisioned as Device Owner, so it can't install updates by itself"

        /** Consecutive 401s before a screen gives up its pairing. Three confirms a genuine
         *  revocation rather than one stray rejection costing somebody a trip to the screen. */
        const val UNAUTHORIZED_BEFORE_REPAIR = 3

        /** How soon to re-check after a 401, while still under [UNAUTHORIZED_BEFORE_REPAIR].
         *  Deliberately much shorter than the normal poll: an admin who just unpaired or
         *  deleted this screen from the CMS is watching it, and there is no reason to make
         *  them wait a full 90 seconds for three confirmations to land on the 30s cadence
         *  when five-second retries confirm just as reliably and finish in well under 20. */
        const val UNAUTHORIZED_RETRY_SECONDS = 5

        // Matches the server's per-heartbeat cap, so a full buffer sends in one go.
        const val MAX_PENDING_PLAYS = 50
        const val MAX_PENDING_ERRORS = 20

        /** How often the preparing screen is refreshed while bytes are landing. */
        const val PREPARING_REFRESH_MILLIS = 250L

        /** Mirrors the playback surface's own cap on a single video (its DEFAULT_VIDEO_CAP_SECONDS
         *  plus slack), so the stall watchdog never fires on a video that is merely long. */
        const val SINGLE_VIDEO_CAP_MILLIS = 95_000L
        /** Slack on top of the longest anything could legitimately take before the loop is
         *  declared stalled — comfortably more than a slow decode, far less than a shift. */
        const val STALL_GRACE_MILLIS = 60_000L

        /** A download is only measured when it is at least this big and took at least this
         *  long — anything smaller is dominated by connection setup, not the link. */
        const val MIN_MEASURED_DOWNLOAD_BYTES = 1_048_576L
        const val MIN_MEASURED_DOWNLOAD_MILLIS = 1_000L
    }

}
