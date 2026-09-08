package com.fortu.player

import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatResponse
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.PairPollResponse
import com.fortu.player.api.PairStartResponse

/**
 * The three things the player's state machine talks to, as interfaces.
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
    suspend fun clear()
}

interface MediaStore {
    fun isCached(item: ManifestItem): Boolean
    fun download(item: ManifestItem)
    fun evictExcept(keep: Collection<String>)
    fun cachedBytes(): Long
}
