package com.fortu.player

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import coil.imageLoader
import coil.request.ImageRequest
import com.fortu.player.api.ApiClient
import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestSlot
import com.fortu.player.data.DeviceStore
import com.fortu.player.data.MediaCache
import com.fortu.player.kiosk.DeviceSettingsApplier
import com.fortu.player.kiosk.SelfUpdater
import com.fortu.player.kiosk.UpdateOutcome
import com.fortu.player.push.MqttPushClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * A thin Android shell around [PlayerEngine].
 *
 * Everything that can be wrong lives in the engine, which has no Android dependencies and is
 * covered by `src/test`. This class only wires the real collaborators together, owns a
 * coroutine scope, and resolves cached files — the parts a JVM test could not exercise
 * meaningfully anyway.
 */
class PlayerViewModel(app: Application) : AndroidViewModel(app) {
    private val api = ApiClient()
    private val store = DeviceStore(app)
    private val cache = MediaCache(app, api.http)
    private val push = MqttPushClient(
        host = BuildConfig.MQTT_HOST,
        port = BuildConfig.MQTT_PORT,
        tls = BuildConfig.MQTT_TLS,
    )

    private val engine = PlayerEngine(
        api = api,
        store = store,
        cache = cache,
        appVersion = BuildConfig.VERSION_NAME,
        apiBaseUrl = BuildConfig.API_BASE_URL,
        canSelfUpdate = { SelfUpdater.isSupported(app) },
        installUpdate = { url -> SelfUpdater.downloadAndInstall(app, api.http, url) },
        consumeInstallFailure = { UpdateOutcome.consumeFailure() },
        applySettings = { settings -> DeviceSettingsApplier.apply(app, settings) },
        currentSettings = { DeviceSettingsApplier.currentSettings(app) },
        applyPower = { on -> DeviceSettingsApplier.applyPower(app, on) },
        warmMedia = { file, kind ->
            when (kind) {
                // Same ImageLoader `AsyncImage` reads from by default (PlaybackSurface never
                // supplies its own) — this decodes into its memory cache, so the real display
                // later is a cache hit instead of a fresh decode.
                "image" -> { app.imageLoader.execute(ImageRequest.Builder(app).data(file).build()); Unit }
                // No equivalent single "decode once" step for video — reading it primes the
                // OS's own page cache, which is most of what makes a second read faster than
                // the first. A bounded buffer: some videos run tens of MB, not worth holding
                // in memory just to throw away.
                "video" -> file.inputStream().use { input ->
                    val buffer = ByteArray(64 * 1024)
                    while (input.read(buffer) != -1) { /* reading is the point */ }
                }
                else -> {}
            }
        },
        push = push,
    )

    val state = engine.state

    /**
     * The engine's own view of things, with the installer's verdict laid over it.
     *
     * `PackageInstaller` reports asynchronously to a BroadcastReceiver (see
     * kiosk/UpdateResultReceiver), which has no way to reach the engine — so the engine's status
     * stops at "installing update X…". Merging the two here is what lets the overlay show how it
     * actually ended: installed, or the reason it did not.
     */
    val debug = combine(engine.debug, UpdateOutcome.last) { debug, outcome ->
        if (outcome == null) debug else debug.copy(updateStatus = outcome)
    }.stateIn(viewModelScope, SharingStarted.Eagerly, DebugInfo(apiBaseUrl = BuildConfig.API_BASE_URL))
    /** Read by the exit-PIN dialog in MainActivity — `settings.appPassword` is the current
     *  configured PIN, or null/blank when exit isn't guarded. */
    val settings = engine.settings

    fun setScreenSize(w: Int, h: Int) = engine.setScreenSize(w, h)
    fun setKioskState(description: String) = engine.setKioskState(description)
    fun reportPlay(slot: ManifestSlot, startedAtMillis: Long, seconds: Int) =
        engine.reportPlay(slot, startedAtMillis, seconds)

    /** Playback failures reach the CMS health page via the next heartbeat, so an unplayable
     *  file is visible as an error rather than only as a gap someone happens to notice. */
    fun reportError(message: String) = engine.reportError(message)

    /** "Check for update" from the debug overlay — the on-screen counterpart to rolling an
     *  update out from the CMS, for exactly the situation that motivated it: an update that
     *  should have landed automatically but has not, and someone is now standing at the
     *  screen wanting it now rather than on the next scheduled heartbeat. */
    fun checkForUpdateNow() = viewModelScope.launch(Dispatchers.IO) { engine.checkForUpdateNow() }

    /** File resolution stays here: it is an Android storage concern, not state-machine logic. */
    fun localFileFor(element: ManifestElement) = cache.fileFor(element.checksum)

    /** True once [engine]'s loop has been launched for this ViewModel instance. */
    private var started = false

    /**
     * Idempotent on purpose. `MainActivity.onCreate` calls this, and `onCreate` can run again
     * on this same, already-running ViewModel — a rotation, or the system recreating the
     * Activity after trimming it in the background — without that meaning "start a second
     * copy of the loop."
     *
     * The bug this fixes: two `engine.run()` coroutines racing the same manifest concurrently
     * downloaded the same file at once, wrote to the same `.part` temp path, and only one
     * `renameTo` could win — the other failed with "could not finalise", and a screen that
     * hit this on every reappearance of the same missing file could never actually cache it.
     */
    fun start() {
        if (started) return
        started = true
        viewModelScope.launch(Dispatchers.IO) { engine.run() }
    }
}
