package com.fortu.player

import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatResponse
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestDevice
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.ManifestPlaylist
import com.fortu.player.api.PairPollResponse
import com.fortu.player.api.PairStartResponse
import com.fortu.player.api.UnauthorizedException
import java.io.IOException

/** Test doubles for the three collaborators [PlayerEngine] talks to. */

class FakeApi : PlayerApi {
    var pairCode = "ABC123"
    var pollToken = "poll-token"
    /** Polls before the code is reported as claimed. */
    var pollsBeforeClaim = 1
    /** Set to make pollPairing report the pairing as gone (expired / already collected). */
    var pairingExpired = false
    var startPairingThrows: Exception? = null

    var manifest: Manifest? = null
    /** Queue of throwables; each fetchManifest pops one and throws it if present. */
    val manifestFailures = ArrayDeque<Exception>()
    var manifestReturns304 = false

    var heartbeatResponse = HeartbeatResponse(version = "v1")
    var heartbeatThrows: Exception? = null

    var startPairingCalls = 0
    var pollCalls = 0
    var manifestCalls = 0
    val heartbeats = mutableListOf<HeartbeatRequest>()

    override fun startPairing(): PairStartResponse {
        startPairingCalls++
        startPairingThrows?.let { throw it }
        return PairStartResponse(
            deviceId = "dev-1",
            pairingCode = pairCode,
            pollToken = pollToken,
            expiresAt = "2026-01-01T00:00:00Z",
            pollSeconds = 5,
        )
    }

    override fun pollPairing(pollToken: String): PairPollResponse? {
        pollCalls++
        if (pairingExpired) return null
        val claimed = pollCalls >= pollsBeforeClaim
        return PairPollResponse(
            claimed = claimed,
            deviceId = "dev-1",
            deviceToken = if (claimed) "device-token" else null,
            name = if (claimed) "Lobby" else null,
        )
    }

    override fun fetchManifest(token: String, etag: String?): Manifest? {
        manifestCalls++
        manifestFailures.removeFirstOrNull()?.let { throw it }
        if (manifestReturns304) return null
        return manifest
    }

    override fun heartbeat(token: String, body: HeartbeatRequest): HeartbeatResponse {
        heartbeats += body
        heartbeatThrows?.let { throw it }
        return heartbeatResponse
    }
}

class FakeStore(
    var storedToken: String? = null,
    var storedEtag: String? = null,
    var storedName: String? = null,
) : TokenStore {
    var clearCount = 0

    override suspend fun token() = storedToken
    override suspend fun etag() = storedEtag
    override suspend fun name() = storedName
    override suspend fun saveToken(token: String, name: String?) {
        storedToken = token
        storedName = name
    }
    override suspend fun saveEtag(etag: String) { storedEtag = etag }
    override suspend fun clear() {
        clearCount++
        storedToken = null
        storedEtag = null
    }
}

class FakeCache : MediaStore {
    val cached = mutableSetOf<String>()
    val downloaded = mutableListOf<String>()
    var downloadThrowsFor: String? = null
    var lastEvictKeep: Collection<String>? = null

    override fun isCached(item: ManifestItem) = item.checksum in cached
    override fun download(item: ManifestItem) {
        if (item.checksum == downloadThrowsFor) throw IOException("download failed")
        downloaded += item.checksum
        cached += item.checksum
    }
    override fun evictExcept(keep: Collection<String>) { lastEvictKeep = keep }
    override fun cachedBytes() = cached.size * 1000L
}

// --- builders -----------------------------------------------------------------------------

fun item(
    checksum: String,
    kind: String = "image",
    seconds: Int = 10,
    fit: String = "contain",
) = ManifestItem(
    id = "item-$checksum",
    mediaId = "media-$checksum",
    kind = kind,
    url = "https://fake/$checksum",
    checksum = checksum,
    bytes = 1000,
    durationSeconds = seconds,
    fit = fit,
)

fun manifest(
    version: String = "v1",
    items: List<ManifestItem> = emptyList(),
    orientation: String = "portrait",
    playlist: ManifestPlaylist? = ManifestPlaylist("pl-1", "Loop", false),
    scheduleName: String? = null,
    validUntil: String? = null,
) = Manifest(
    version = version,
    device = ManifestDevice(name = "Lobby", orientation = orientation),
    playlist = if (items.isEmpty() && playlist == null) null else playlist,
    items = items,
    scheduleName = scheduleName,
    validUntil = validUntil,
)

fun unauthorized() = UnauthorizedException()
