package com.fortu.player

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fortu.player.api.ApiClient
import com.fortu.player.api.ManifestItem
import com.fortu.player.data.DeviceStore
import com.fortu.player.data.MediaCache
import com.fortu.player.kiosk.SelfUpdater
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

    private val engine = PlayerEngine(
        api = api,
        store = store,
        cache = cache,
        appVersion = BuildConfig.VERSION_NAME,
        apiBaseUrl = BuildConfig.API_BASE_URL,
        canSelfUpdate = { SelfUpdater.isSupported(app) },
        installUpdate = { url -> SelfUpdater.downloadAndInstall(app, api.http, url) },
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

    fun start() {
        viewModelScope.launch(Dispatchers.IO) { engine.run() }
    }
}
