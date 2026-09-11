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
    /** This device's own MQTT password, rides along with deviceToken for the same reason —
     *  see TokenStore.mqttPassword. Absent when MQTT is disabled or provisioning failed. */
    @SerialName("mqtt_password") val mqttPassword: String? = null,
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
     *  proof-of-play; the server resolves the filename from it.
     *
     * Defaulted, like every field added after the first release: a screen must keep playing
     * against a backend that is a deploy or two behind, because in a real fleet the two
     * never update at the same moment. Missing it costs proof-of-play, not playback. */
    @SerialName("media_id") val mediaId: String? = null,
    val kind: String,
    val url: String,
    val checksum: String,
    val bytes: Long,
    @SerialName("duration_seconds") val durationSeconds: Int,
    /** Defaulted for the same version-skew reason: an older backend that does not send it
     *  should letterbox rather than stop the screen. */
    val fit: String = "contain",
    /** Video only. Every video is muted unless this is set — defaulted false so an older
     *  backend that predates this field keeps every screen silent, not suddenly audible. */
    @SerialName("has_audio") val hasAudio: Boolean = false,
)

/**
 * Remotely-configured values from the CMS's device-settings registry (backend
 * `services/device_settings.py`). Typed fields for what this build knows how to apply —
 * `touchscreen_disabled` and `power_schedule` arrive in the same JSON object but have no
 * field here yet, so `ignoreUnknownKeys` on the shared [kotlinx.serialization.json.Json]
 * instance just drops them; they cost nothing to add later, the same way every field below
 * did.
 */
@Serializable
data class ManifestSettings(
    /** 0-100. Applied to `STREAM_MUSIC` — see `kiosk/DeviceSettingsApplier.kt`. */
    val volume: Int? = null,
    /** 0-100. Requires Device Owner to actually take effect; degrades to a no-op otherwise,
     *  same as everything else in `kiosk/`. */
    val brightness: Int? = null,
    /** The PIN required to exit kiosk mode from the debug overlay. Null or blank means no
     *  PIN is configured, and exit is unguarded. Compared in `MainActivity`, never applied
     *  as a system side effect like the two above. */
    @SerialName("app_password") val appPassword: String? = null,
    /** A direct, unscheduled override of the screen's power state — see
     *  `kiosk/DeviceSettingsApplier.applyPower`. Independent of `power_schedule`, which this
     *  build does not apply at all yet. */
    @SerialName("power_on") val powerOn: Boolean? = null,
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
    /** Defaulted for the same version-skew reason as every field above: an older backend
     *  that predates settings entirely sends no key, and this becomes "nothing configured"
     *  rather than a parse failure. */
    val settings: ManifestSettings = ManifestSettings(),
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
    /** What settings.volume/brightness actually are right now, read straight from the
     *  system (`DeviceSettingsApplier.currentSettings`) — distinct from [ManifestSettings],
     *  which is what the CMS wants them to be. `Int`-only for now, matching the two settings
     *  that are genuine system side effects; a future non-numeric reportable setting would
     *  need this typed more generally. */
    @SerialName("reported_settings") val reportedSettings: Map<String, Int>? = null,
)

@Serializable
data class UpdateInfo(val version: String, val url: String)

@Serializable
data class HeartbeatResponse(
    val version: String,
    /** Non-null when the server has published a build this screen isn't running. */
    val update: UpdateInfo? = null,
)
