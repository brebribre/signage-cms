package com.fortu.player

import com.fortu.player.api.HeartbeatRequest
import com.fortu.player.api.HeartbeatResponse
import com.fortu.player.api.Manifest
import com.fortu.player.api.ManifestDevice
import com.fortu.player.api.ManifestElement
import com.fortu.player.api.ManifestItem
import com.fortu.player.api.ManifestPlaylist
import com.fortu.player.api.ManifestSlot
import com.fortu.player.api.PairPollResponse
import com.fortu.player.api.PairStartResponse
import com.fortu.player.api.UpdateStatusReport
import com.fortu.player.api.UnauthorizedException
import java.io.File
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
    /** Rides along with deviceToken on the claimed poll, like the real mqtt_admin-provisioned
     *  one — null here means "MQTT disabled," same as the real server's response. */
    var mqttPasswordOnClaim: String? = "mqtt-secret-1"

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

    /** The mounting the player reported, per call, so a test can assert it was sent. */
    val detectedOrientations = mutableListOf<String?>()

    override fun startPairing(detectedOrientation: String?): PairStartResponse {
        startPairingCalls++
        detectedOrientations += detectedOrientation
        startPairingThrows?.let { throw it }
        return PairStartResponse(
            deviceId = "dev-1",
            pairingCode = pairCode,
            pollToken = pollToken,
            expiresAt = "2026-01-01T00:00:00Z",
            pollSeconds = 5,
        )
    }

    override fun pollPairing(pollToken: String, detectedOrientation: String?): PairPollResponse? {
        pollCalls++
        detectedOrientations += detectedOrientation
        if (pairingExpired) return null
        val claimed = pollCalls >= pollsBeforeClaim
        return PairPollResponse(
            claimed = claimed,
            deviceId = "dev-1",
            deviceToken = if (claimed) "device-token" else null,
            mqttPassword = if (claimed) mqttPasswordOnClaim else null,
            name = if (claimed) "Lobby" else null,
        )
    }

    /** ETags actually seen, so a test can assert what the player sent. */
    val etagsSeen = mutableListOf<String?>()

    /** When true, behave like the real server: answer 304 whenever the ETag matches the
     *  current manifest version. Without this a reboot test cannot reproduce the bug where a
     *  persisted ETag left a restarted screen with nothing to show. */
    var honourEtag = false

    override fun fetchManifest(token: String, etag: String?): Manifest? {
        manifestCalls++
        etagsSeen += etag
        manifestFailures.removeFirstOrNull()?.let { throw it }
        if (manifestReturns304) return null
        if (honourEtag && etag != null && etag == "\"${manifest?.version}\"") return null
        return manifest
    }

    override fun heartbeat(token: String, body: HeartbeatRequest): HeartbeatResponse {
        heartbeats += body
        heartbeatThrows?.let { throw it }
        return heartbeatResponse
    }

    /** Every update-status report, in order — what the CMS would have seen. */
    val updateReports = mutableListOf<UpdateStatusReport>()
    var updateReportThrows: Exception? = null

    override fun reportUpdateStatus(token: String, body: UpdateStatusReport) {
        updateReports += body
        updateReportThrows?.let { throw it }
    }
}

class FakeStore(
    var storedToken: String? = null,
    var storedEtag: String? = null,
    var storedName: String? = null,
    var storedManifestJson: String? = null,
    var storedDeviceId: String? = null,
    var storedMqttPassword: String? = null,
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
    override suspend fun manifestJson() = storedManifestJson
    override suspend fun saveManifestJson(json: String) { storedManifestJson = json }
    override suspend fun deviceId() = storedDeviceId
    override suspend fun saveDeviceId(id: String) { storedDeviceId = id }
    override suspend fun mqttPassword() = storedMqttPassword
    override suspend fun saveMqttPassword(password: String) { storedMqttPassword = password }
    override suspend fun clear() {
        clearCount++
        storedToken = null
        storedEtag = null
        storedManifestJson = null
        storedDeviceId = null
        storedMqttPassword = null
    }
}

/** Records connect/disconnect calls and lets a test fire a push on demand. */
class FakePushClient : PushClient {
    val connectedTo = mutableListOf<String>()
    val passwordsSeen = mutableListOf<String>()
    var disconnectCount = 0
    private val _signal = kotlinx.coroutines.flow.MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    override val signal: kotlinx.coroutines.flow.SharedFlow<Unit> = _signal

    override fun connect(deviceId: String, password: String) {
        connectedTo += deviceId
        passwordsSeen += password
    }
    override fun disconnect() { disconnectCount++ }

    /** Simulates the CMS having just published a change for this device. */
    fun push() { _signal.tryEmit(Unit) }
}

class FakeCache : MediaStore {
    val cached = mutableSetOf<String>()
    val downloaded = mutableListOf<String>()
    var downloadThrowsFor: String? = null
    var lastEvictKeep: Collection<String>? = null

    override fun isCached(checksum: String, bytes: Long) = checksum in cached
    override fun download(checksum: String, url: String, onProgress: (Long) -> Unit) {
        if (checksum == downloadThrowsFor) throw IOException("download failed")
        onProgress(500)
        onProgress(1000)
        downloaded += checksum
        cached += checksum
    }
    override fun evictExcept(keep: Collection<String>) { lastEvictKeep = keep }
    override fun cachedBytes() = cached.size * 1000L
    override fun fileFor(checksum: String) = File("/fake/$checksum")
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

/** Wraps one or more [item]s into the multi-element `ManifestSlot` shape — for tests that need
 *  to exercise `slots` (rather than the flat `items`) directly, e.g. proof-of-play or the
 *  multi-element download/cache logic. */
fun slot(vararg items: ManifestItem, seconds: Int = 10) = ManifestSlot(
    id = "slot-${items.joinToString("-") { it.checksum }}",
    durationSeconds = seconds,
    elements = items.map {
        ManifestElement(
            id = it.id,
            mediaId = it.mediaId,
            kind = it.kind,
            url = it.url,
            checksum = it.checksum,
            bytes = it.bytes,
            fit = it.fit,
            hasAudio = it.hasAudio,
        )
    },
)

fun manifest(
    version: String = "v1",
    items: List<ManifestItem> = emptyList(),
    /** The real multi-element shape, for tests exercising `slots` directly rather than the
     *  flat back-compat `items`. Independent of `items` — a test builds one or the other. */
    slots: List<ManifestSlot> = emptyList(),
    orientation: String = "portrait",
    playlist: ManifestPlaylist? = ManifestPlaylist("pl-1", "Loop", false),
    scheduleName: String? = null,
    validUntil: String? = null,
) = Manifest(
    version = version,
    device = ManifestDevice(name = "Lobby", orientation = orientation),
    playlist = if (items.isEmpty() && slots.isEmpty() && playlist == null) null else playlist,
    items = items,
    slots = slots,
    scheduleName = scheduleName,
    validUntil = validUntil,
)

fun unauthorized() = UnauthorizedException()
fun disconnected() = com.fortu.player.api.DisconnectedException()
