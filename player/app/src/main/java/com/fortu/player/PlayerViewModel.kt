package com.fortu.player

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fortu.player.api.ApiClient
import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatScreen
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.UnauthorizedException
import com.fortu.player.data.DeviceStore
import com.fortu.player.data.MediaCache
import com.fortu.player.kiosk.SelfUpdater
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "FortuPlayer"

/** Everything the UI can be showing. The pairing screen doubles as the error state. */
sealed interface PlayerState {
    data object Starting : PlayerState
    /** Unpaired, revoked, or 401'd — always lands here rather than on a black screen,
     *  because a screen showing a pairing code is diagnosable from across the room. */
    data class Pairing(val code: String, val error: String? = null) : PlayerState
    /** Paired but nothing assigned. A valid state, not an error. */
    data class Idle(val deviceName: String) : PlayerState
    data class Playing(val items: List<ManifestItem>, val shuffle: Boolean) : PlayerState
}

data class DebugInfo(
    val deviceName: String? = null,
    val version: String? = null,
    val cachedBytes: Long = 0,
    val itemCount: Int = 0,
    val lastPoll: String = "never",
    val lastError: String? = null,
    val apiBaseUrl: String = BuildConfig.API_BASE_URL,
    /** Whether Device Owner provisioning actually took — the one thing you cannot tell by
     *  looking at a screen, and the difference between a kiosk and a phone showing an app. */
    val kiosk: String = "unknown",
)

class PlayerViewModel(app: Application) : AndroidViewModel(app) {
    private val api = ApiClient()
    private val store = DeviceStore(app)
    private val cache = MediaCache(app)

    private val _state = MutableStateFlow<PlayerState>(PlayerState.Starting)
    val state = _state.asStateFlow()

    private val _debug = MutableStateFlow(DebugInfo())
    val debug = _debug.asStateFlow()

    private var screenWidth = 0
    private var screenHeight = 0

    /** One install attempt per process. Without this a failing install would be retried on
     *  every heartbeat — a screen re-downloading an APK every 30 seconds forever, which is
     *  worse than simply not updating. A restart is a deliberate second chance. */
    private var updateAttempted = false

    fun setScreenSize(w: Int, h: Int) { screenWidth = w; screenHeight = h }

    fun setKioskState(description: String) {
        _debug.update { it.copy(kiosk = description) }
    }

    fun start() {
        viewModelScope.launch(Dispatchers.IO) { runForever() }
    }

    private suspend fun runForever() {
        while (true) {
            try {
                val token = store.token() ?: pairUntilClaimed() ?: continue
                syncAndPlay(token)
            } catch (e: UnauthorizedException) {
                // The screen was unpaired or deleted in the CMS. Drop everything and show a
                // fresh code rather than sitting on a dead token.
                Log.w(TAG, "token rejected, re-pairing")
                store.clear()
                _state.value = PlayerState.Starting
            } catch (e: Exception) {
                Log.e(TAG, "loop error", e)
                _debug.update { it.copy(lastError = e.message) }
                delay(POLL_SECONDS * 1000L)
            }
        }
    }

    /** Shows a code and polls until a human claims it. Returns the new device token. */
    private suspend fun pairUntilClaimed(): String? {
        val pair = try {
            api.startPairing()
        } catch (e: Exception) {
            // No network yet: say so on screen instead of showing a code that cannot work.
            _state.value = PlayerState.Pairing("······", "Cannot reach ${BuildConfig.API_BASE_URL}")
            delay(5_000)
            return null
        }

        _state.value = PlayerState.Pairing(pair.pairingCode)

        while (true) {
            delay(pair.pollSeconds * 1000L)
            val poll = try {
                api.pollPairing(pair.pollToken)
            } catch (e: Exception) {
                _debug.update { it.copy(lastError = e.message) }
                continue
            }
            // 404 → the code expired. Start over with a fresh one rather than showing a
            // stale code nobody can claim.
            if (poll == null) return null
            val token = poll.deviceToken
            if (poll.claimed && token != null) {
                store.saveToken(token, poll.name)
                _debug.update { it.copy(deviceName = poll.name) }
                return token
            }
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
                val res = api.heartbeat(
                    token,
                    HeartbeatRequest(
                        appVersion = BuildConfig.VERSION_NAME,
                        screen = if (screenWidth > 0) HeartbeatScreen(screenWidth, screenHeight) else null,
                        currentItemId = null,
                        errors = emptyList(),
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
            delay(POLL_SECONDS * 1000L)
        }
    }

    private suspend fun applyManifest(manifest: Manifest) = withContext(Dispatchers.IO) {
        _debug.update {
            it.copy(
                deviceName = manifest.device.name,
                version = manifest.version,
                itemCount = manifest.items.size,
            )
        }

        if (manifest.items.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name)
            cache.evictExcept(emptyList())
            _debug.update { it.copy(cachedBytes = cache.cachedBytes()) }
            return@withContext
        }

        // Download everything missing BEFORE switching the playlist, so a screen never shows
        // a gap while a file is still arriving.
        for (item in manifest.items) {
            if (!cache.isCached(item)) {
                Log.i(TAG, "downloading ${item.checksum} (${item.bytes} bytes)")
                try {
                    cache.download(api.http, item)
                } catch (e: Exception) {
                    Log.e(TAG, "download failed for ${item.id}", e)
                    _debug.update { it.copy(lastError = "download: ${e.message}") }
                    // Keep going: one bad item should not stop the rest of the loop from
                    // updating. The player skips anything still missing.
                }
            }
        }

        val playable = manifest.items.filter { cache.isCached(it) }
        if (playable.isEmpty()) {
            _state.value = PlayerState.Idle(manifest.device.name)
        } else {
            _state.value = PlayerState.Playing(playable, manifest.playlist?.shuffle ?: false)
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
        if (!SelfUpdater.isSupported(getApplication())) {
            Log.i(TAG, "update $version available but this device cannot install silently")
            updateAttempted = true
            return
        }
        updateAttempted = true
        Log.i(TAG, "installing update $version")
        _debug.update { it.copy(lastError = "installing update $version…") }
        val ok = SelfUpdater.downloadAndInstall(getApplication(), api.http, url)
        if (!ok) {
            _debug.update { it.copy(lastError = "update $version failed — see logcat") }
        }
    }

    fun localFileFor(item: ManifestItem) = cache.fileFor(item.checksum)

    companion object {
        const val POLL_SECONDS = 30
    }
}
