package com.fortu.player

import android.util.Log
import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatScreen
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.PlayReport
import com.fortu.player.api.UnauthorizedException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.withContext

private const val TAG = "FortuPlayer"

/** Everything the UI can be showing. The pairing screen doubles as the error state. */
sealed interface PlayerState {
    data object Starting : PlayerState

    /** Unpaired, revoked, or 401'd — always lands here rather than on a black screen,
     *  because a screen showing a pairing code is diagnosable from across the room.
     *
     * `apiHost` is displayed deliberately: pairing fails silently and confusingly when the
     * screen and the CMS are talking to different servers, and the only way to notice is to
     * see which one the screen is using. */
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
        val done: Int,
        val total: Int,
        val currentFile: String?,
    ) : PlayerState

    /** Paired but nothing assigned. A valid state, not an error. */
    data class Idle(val deviceName: String, val orientation: String? = null) : PlayerState

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
        val items: List<ManifestItem>,
        val shuffle: Boolean,
        val orientation: String? = null,
    ) : PlayerState
}


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
)


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
    private val installUpdate: (String) -> Boolean = { false },
    /** Where blocking work runs. Injected so tests can supply the test scheduler's
     *  dispatcher — with a hard-coded `Dispatchers.IO` the download and state-transition work
     *  escapes virtual time entirely and assertions race it. */
    private val io: CoroutineDispatcher = Dispatchers.IO,
) {
    private val _state = MutableStateFlow<PlayerState>(PlayerState.Starting)
    val state = _state.asStateFlow()

    private val _debug = MutableStateFlow(DebugInfo(apiBaseUrl = apiBaseUrl))
    val debug = _debug.asStateFlow()

    private var screenWidth = 0
    private var screenHeight = 0

    /** One install attempt per process. Without this a failing install would be retried on
     *  every heartbeat — a screen re-downloading an APK every 30 seconds forever, which is
     *  worse than simply not updating. A restart is a deliberate second chance. */
    private var updateAttempted = false

    /** When the current schedule window ends, as epoch millis. The poll interval is
     *  shortened to land on it. */
    private var validUntilMillis: Long? = null

    /** Plays observed since the last heartbeat, drained when one is sent.
     *  Bounded so a screen that cannot reach the server for hours accumulates a report
     *  instead of unbounded memory — the oldest entries are the ones worth dropping. */
    private val pendingPlays = java.util.Collections.synchronizedList(mutableListOf<PlayReport>())

    /** Errors observed since the last heartbeat, reported the same way. */
    private val pendingErrors = java.util.Collections.synchronizedList(mutableListOf<String>())

    fun setScreenSize(w: Int, h: Int) { screenWidth = w; screenHeight = h }

    fun setKioskState(description: String) {
        _debug.update { it.copy(kiosk = description) }
    }

    suspend fun run() {
        runForever()
    }

    private suspend fun runForever() {
        val host = apiBaseUrl.substringAfter("://").substringBefore("/")
        var consecutiveFailures = 0
        var unauthorizedStreak = 0

        while (true) {
            try {
                val token = store.token() ?: pairUntilClaimed() ?: continue
                syncAndPlay(token)
                consecutiveFailures = 0
                unauthorizedStreak = 0
            } catch (e: UnauthorizedException) {
                // Discarding the token is destructive and irreversible *from the device*:
                // somebody has to physically walk to the screen and re-pair it. A single 401
                // is not enough evidence to do that — a request landing mid-deploy, a proxy
                // hiccup or a brief server fault would permanently unpair a working screen.
                //
                // So require several in a row. A genuine unpair or delete answers 401 every
                // time and still takes effect within a couple of minutes; a transient one
                // costs nothing and is forgotten on the next success.
                unauthorizedStreak++
                Log.w(TAG, "token rejected ($unauthorizedStreak/$UNAUTHORIZED_BEFORE_REPAIR)")
                if (unauthorizedStreak >= UNAUTHORIZED_BEFORE_REPAIR) {
                    Log.w(TAG, "token rejected repeatedly — clearing and re-pairing")
                    store.clear()
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
                    delay(POLL_SECONDS * 1000L)
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

        while (true) {
            val etag = store.etag()
            val manifest = api.fetchManifest(token, etag)

            _debug.update { it.copy(lastPoll = "just now", lastError = null) }

            if (manifest != null) {
                applyManifest(manifest)
                store.saveEtag("\"${manifest.version}\"")
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
                    ),
                )
                res.update?.let { maybeSelfUpdate(it.version, it.url) }

                if (etag != null && "\"${res.version}\"" != etag) {
                    // Version moved under us — loop immediately rather than waiting.
                    continue
                }
            } catch (e: UnauthorizedException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "heartbeat failed (continuing)", e)
            }

            beatsSincePoll++
            delay(nextPollDelayMillis())
        }
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

    private fun parseInstantMillis(iso: String?): Long? = try {
        if (iso == null) null
        else java.time.Instant.parse(iso.replace("+00:00", "Z")).toEpochMilli()
    } catch (e: Exception) {
        Log.w(TAG, "unparseable valid_until: $iso")
        null
    }

    private suspend fun applyManifest(manifest: Manifest) = withContext(io) {
        validUntilMillis = parseInstantMillis(manifest.validUntil)
        _debug.update {
            it.copy(
                deviceName = manifest.device.name,
                version = manifest.version,
                itemCount = manifest.items.size,
                schedule = manifest.scheduleName,
            )
        }

        if (manifest.items.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name, manifest.device.orientation)
            cache.evictExcept(emptyList())
            _debug.update { it.copy(cachedBytes = cache.cachedBytes()) }
            return@withContext
        }

        // Download everything missing BEFORE switching the playlist, so a screen never shows
        // a gap while a file is still arriving.
        val missing = manifest.items.filter { !cache.isCached(it) }
        // Only announce preparing when there is genuinely something to fetch — a routine poll
        // that changes nothing must not flash a progress screen over content that is playing.
        if (missing.isNotEmpty()) {
            _state.value = PlayerState.Preparing(
                manifest.device.name, 0, missing.size, null,
            )
        }
        var fetched = 0

        for (item in manifest.items) {
            if (!cache.isCached(item)) {
                Log.i(TAG, "downloading ${item.checksum} (${item.bytes} bytes)")
                _state.value = PlayerState.Preparing(
                    manifest.device.name, fetched, missing.size,
                    "${item.kind} · ${item.bytes / 1_048_576} MB",
                )
                try {
                    cache.download(item)
                } catch (e: Exception) {
                    Log.e(TAG, "download failed for ${item.id}", e)
                    _debug.update { it.copy(lastError = "download: ${e.message}") }
                    // Keep going: one bad item should not stop the rest of the loop from
                    // updating. The player skips anything still missing.
                }
                fetched++
            }
        }

        val playable = manifest.items.filter { cache.isCached(it) }
        if (playable.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name, manifest.device.orientation)
        } else {
            _state.value = PlayerState.Playing(
                playable,
                manifest.playlist?.shuffle ?: false,
                manifest.device.orientation,
            )
        }

        // Evict only after the new set is safely on disk.
        cache.evictExcept(manifest.items.map { it.checksum })
        _debug.update { it.copy(cachedBytes = cache.cachedBytes()) }
    }

    /**
     * Install a published build over ourselves, if this screen is provisioned to do so.
     *
     * Silently declines on anything that isn't Device Owner. That is not a failure worth
     * surfacing on screen: a sideloaded or development install simply updates by hand, and
     * the alternative — the system's confirmation dialog — would park the screen on a prompt
     * nobody is standing in front of.
     */
    private fun maybeSelfUpdate(version: String, url: String) {
        if (updateAttempted) return
        if (!canSelfUpdate()) {
            Log.i(TAG, "update $version available but this device cannot install silently")
            updateAttempted = true
            return
        }
        updateAttempted = true
        Log.i(TAG, "installing update $version")
        _debug.update { it.copy(lastError = "installing update $version…") }
        val ok = installUpdate(url)
        if (!ok) {
            _debug.update { it.copy(lastError = "update $version failed — see logcat") }
        }
    }

    /** Called by the playback surface each time an item finishes. */
    fun reportPlay(item: ManifestItem, startedAtMillis: Long, seconds: Int) {
        synchronized(pendingPlays) {
            if (pendingPlays.size >= MAX_PENDING_PLAYS) pendingPlays.removeAt(0)
            pendingPlays.add(
                PlayReport(
                    // Null against an older backend that does not send it. The server then
                    // falls back to whatever filename it can resolve, and the play is still
                    // recorded rather than dropped.
                    mediaId = item.mediaId,
                    // Left blank on purpose: the server resolves the real name from mediaId,
                    // so the log cannot drift when a file is renamed.
                    filename = "",
                    startedAt = java.time.Instant.ofEpochMilli(startedAtMillis).toString(),
                    seconds = seconds,
                )
            )
        }
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

        /** Consecutive 401s before a screen gives up its pairing. Three, at 30s apart, means
         *  a genuine unpair still takes effect within ~90 seconds while a transient rejection
         *  cannot cost somebody a trip to the screen. */
        const val UNAUTHORIZED_BEFORE_REPAIR = 3

        // Matches the server's per-heartbeat cap, so a full buffer sends in one go.
        const val MAX_PENDING_PLAYS = 50
        const val MAX_PENDING_ERRORS = 20
    }

}
