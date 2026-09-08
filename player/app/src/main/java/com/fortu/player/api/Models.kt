package com.fortu.player.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors the backend's device-sync schemas. Field names match the JSON exactly. */

@Serializable
data class PairStartResponse(
    @SerialName("device_id") val deviceId: String,
    @SerialName("pairing_code") val pairingCode: String,
    @SerialName("poll_token") val pollToken: String,
    @SerialName("expires_at") val expiresAt: String,
    @SerialName("poll_seconds") val pollSeconds: Int,
)

@Serializable
data class PairPollResponse(
    val claimed: Boolean,
    @SerialName("device_id") val deviceId: String,
    /** Present exactly once, on the first poll after a human claims the screen. */
    @SerialName("device_token") val deviceToken: String? = null,
    val name: String? = null,
)

@Serializable
data class ManifestDevice(val name: String, val orientation: String)

@Serializable
data class ManifestPlaylist(val id: String, val name: String, val shuffle: Boolean)

@Serializable
data class ManifestItem(
    val id: String,
    /** The underlying media, distinct from `id` (the playlist slot). Reported back for
     *  proof-of-play; the server resolves the filename from it. */
    @SerialName("media_id") val mediaId: String,
    val kind: String,
    val url: String,
    val checksum: String,
    val bytes: Long,
    @SerialName("duration_seconds") val durationSeconds: Int,
    val fit: String,
)

@Serializable
data class Manifest(
    val version: String,
    val device: ManifestDevice,
    /** null is a valid state — a newly paired screen with nothing assigned yet. */
    val playlist: ManifestPlaylist? = null,
    val items: List<ManifestItem> = emptyList(),
    /** The schedule currently overriding the default, if any. Shown in the debug overlay so
     *  "why is this playing?" is answerable at the screen. */
    @SerialName("schedule_name") val scheduleName: String? = null,
    /** ISO-8601 UTC instant at which this answer stops being true. The player polls sooner
     *  than its usual interval when a boundary is closer, so a daypart change lands on time
     *  rather than up to a full poll late. */
    @SerialName("valid_until") val validUntil: String? = null,
)

@Serializable
data class HeartbeatScreen(val width: Int, val height: Int)

@Serializable
data class PlayReport(
    @SerialName("media_id") val mediaId: String? = null,
    val filename: String = "",
    /** ISO-8601 UTC. */
    @SerialName("started_at") val startedAt: String,
    val seconds: Int = 0,
)

@Serializable
data class HeartbeatRequest(
    @SerialName("app_version") val appVersion: String? = null,
    val screen: HeartbeatScreen? = null,
    @SerialName("current_item_id") val currentItemId: String? = null,
    val errors: List<String> = emptyList(),
    /** Batched since the last heartbeat. An item can be shorter than the heartbeat interval,
     *  so reporting only what is on screen right now would miss most of the loop. */
    val plays: List<PlayReport> = emptyList(),
)

@Serializable
data class UpdateInfo(val version: String, val url: String)

@Serializable
data class HeartbeatResponse(
    val version: String,
    /** Non-null when the server has published a build this screen isn't running. */
    val update: UpdateInfo? = null,
)
