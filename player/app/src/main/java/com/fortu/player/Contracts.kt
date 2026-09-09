package com.fortu.player

import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatResponse
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.PairPollResponse
import com.fortu.player.api.PairStartResponse
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * The things the player's state machine talks to, as interfaces.
 *
 * They exist so [PlayerEngine] can be exercised on a plain JVM with fakes. Before this, the
 * ViewModel constructed `ApiClient`, `DeviceStore` and `MediaCache` itself, which meant the
 * loop could only be tested by installing the app on a device and watching it — and five real
 * bugs reached hardware precisely because nothing else could catch them.
 */

interface PlayerApi {
    fun startPairing(): PairStartResponse
    /** Null when the pairing expired or was already collected (HTTP 404). */
    fun pollPairing(pollToken: String): PairPollResponse?
    /** Null when the server answered 304 — nothing changed. */
    fun fetchManifest(token: String, etag: String?): Manifest?
    fun heartbeat(token: String, body: HeartbeatRequest): HeartbeatResponse
}

interface TokenStore {
    suspend fun token(): String?
    suspend fun etag(): String?
    suspend fun name(): String?
    suspend fun saveToken(token: String, name: String?)
    suspend fun saveEtag(etag: String)
    /** The last manifest, as JSON.
     *
     * Persisted so a screen that reboots can play immediately from its cache, with no network
     * at all. Without it the ETag survives a restart while the content does not, and the
     * server's correct 304 leaves the player with nothing to show. */
    suspend fun manifestJson(): String?
    suspend fun saveManifestJson(json: String)
    /** This screen's own id, learned once at pairing.
     *
     * Every HTTP call authenticates by bearer token alone and never needed this — it exists
     * purely so the device can subscribe to its own push topic (`devices/{id}/manifest`, see
     * backend/app/infra/mqtt.py). A screen paired by an older build that never saved one
     * simply has no id to subscribe with; see [PushClient] for what that degrades to. */
    suspend fun deviceId(): String?
    suspend fun saveDeviceId(id: String)
    suspend fun clear()
}

interface MediaStore {
    fun isCached(item: ManifestItem): Boolean
    fun download(item: ManifestItem)
    fun evictExcept(keep: Collection<String>)
    fun cachedBytes(): Long
}

/**
 * A low-latency nudge that the manifest may have changed, so the poll loop can skip the rest
 * of its current wait instead of sitting out the full interval.
 *
 * Deliberately optional in every sense: [connect] and [disconnect] are no-ops for an
 * implementation with nothing to connect to, and a [signal] that never emits is exactly "no
 * push available" — the loop falls back to its plain poll cadence, unchanged. Nothing about
 * this is a dependency; the manifest's ETag remains the one source of truth regardless of
 * whether a push ever arrives.
 */
interface PushClient {
    /** Safe to call repeatedly — an implementation already connected to this id no-ops. */
    fun connect(deviceId: String)
    fun disconnect()
    val signal: SharedFlow<Unit>
}

/** The default: nothing to connect to, nothing ever emitted. */
object NoopPushClient : PushClient {
    override fun connect(deviceId: String) {}
    override fun disconnect() {}
    override val signal: SharedFlow<Unit> = MutableSharedFlow()
}
