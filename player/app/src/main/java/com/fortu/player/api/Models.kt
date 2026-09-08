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
)

@Serializable
data class HeartbeatScreen(val width: Int, val height: Int)

@Serializable
data class HeartbeatRequest(
    @SerialName("app_version") val appVersion: String? = null,
    val screen: HeartbeatScreen? = null,
    @SerialName("current_item_id") val currentItemId: String? = null,
    val errors: List<String> = emptyList(),
)

@Serializable
data class HeartbeatResponse(val version: String)
