package com.fortu.player

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fortu.player.api.ApiClient
import com.fortu.player.api.ManifestItem
import com.fortu.player.data.DeviceStore
import com.fortu.player.data.MediaCache
import com.fortu.player.kiosk.SelfUpdater
import com.fortu.player.push.MqttPushClient
import kotlinx.coroutines.Dispatchers
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
        username = BuildConfig.MQTT_USERNAME,
        password = BuildConfig.MQTT_PASSWORD,
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
        push = push,
    )

    val state = engine.state
    val debug = engine.debug

    fun setScreenSize(w: Int, h: Int) = engine.setScreenSize(w, h)
    fun setKioskState(description: String) = engine.setKioskState(description)
    fun reportPlay(item: ManifestItem, startedAtMillis: Long, seconds: Int) =
        engine.reportPlay(item, startedAtMillis, seconds)

    /** Playback failures reach the CMS health page via the next heartbeat, so an unplayable
     *  file is visible as an error rather than only as a gap someone happens to notice. */
    fun reportError(message: String) = engine.reportError(message)

    /** File resolution stays here: it is an Android storage concern, not state-machine logic. */
    fun localFileFor(item: ManifestItem) = cache.fileFor(item.checksum)

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
