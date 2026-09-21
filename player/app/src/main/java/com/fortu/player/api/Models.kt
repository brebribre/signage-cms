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
data class ManifestDevice(
    val name: String,
    /** "portrait"/"landscape" — what this field meant before [rotation] existed. */
    val orientation: String,
    /** 0, 90, 180 or 270: the turn to apply to content, clockwise. Null from a backend that
     *  predates it, in which case [orientation] decides. */
    val rotation: Int? = null,
    /** IANA name the CMS schedules this screen in — the power schedule is evaluated on it.
     *  Defaulted for version skew: an older backend sends none, and the screen falls back to
     *  its own system timezone. */
    val timezone: String? = null,
)

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
 * One element within a [ManifestSlot] — the real, unflattened shape (backend
 * `schemas/device_sync.py`'s `ManifestElement`). Everything [ManifestItem] has, plus where and
 * how it sits within its slot: multiple elements share one slot's screen space instead of each
 * getting the whole thing.
 *
 * Every field but `id`/`kind`/`url`/`checksum`/`bytes` is defaulted for the same version-skew
 * reason as [ManifestItem]'s own fields — this type is newer than the backend that might be
 * answering, and a manifest missing a field must degrade sensibly rather than fail to parse.
 */
@Serializable
data class ManifestElement(
    val id: String,
    @SerialName("media_id") val mediaId: String? = null,
    /** "image", "video", or [KIND_WEB] — a website loaded live from [url], with nothing to
     *  download ([checksum] is derived from the address, [bytes] is 0). */
    val kind: String,
    val url: String,
    val checksum: String,
    val bytes: Long,
    val x: Float = 0f,
    val y: Float = 0f,
    val width: Float = 1f,
    val height: Float = 1f,
    val fit: String = "contain",
    @SerialName("has_audio") val hasAudio: Boolean = false,
    @SerialName("rotation_degrees") val rotationDegrees: Int = 0,
    @SerialName("crop_x") val cropX: Float? = null,
    @SerialName("crop_y") val cropY: Float? = null,
    @SerialName("crop_zoom") val cropZoom: Float? = null,
    /** A video's thumbnail — what a blurred scene background shows for it
     *  (see playback/SceneBackground.kt). Null for anything else, or an older backend. */
    @SerialName("poster_url") val posterUrl: String? = null,
    /** A [KIND_TEXT] element's words and look, drawn by the player itself. Null otherwise. */
    val text: String? = null,
    @SerialName("text_style") val textStyle: TextStyle? = null,
)

/** How a text element looks — the backend's TextStyle. [size] is a fraction of the screen's
 *  height, so a scene reads the same on every panel. */
@Serializable
data class TextStyle(
    val size: Float = 0.06f,
    val color: String = "#FFFFFF",
    val weight: String = "bold",
    val align: String = "center",
    val background: String? = null,
)

/** A text element: drawn from [ManifestElement.text], never downloaded or cached. */
const val KIND_TEXT = "text"

/** A website element: shown live in a WebView, never downloaded or cached. */
const val KIND_WEB = "web"

/** One playable slot — one or more layered [ManifestElement]s, shown together for
 *  [durationSeconds] before the loop advances. */
@Serializable
data class ManifestSlot(
    val id: String,
    @SerialName("duration_seconds") val durationSeconds: Int,
    val elements: List<ManifestElement> = emptyList(),
    /** "black", "blur" (a blurred copy of the scene's largest picture or video fills what the
     *  elements don't cover) or "color" ([backgroundColor]). Defaulted to black, which is what
     *  every older build shows. */
    val background: String = "black",
    /** With background "color": the `#RRGGBB` to paint behind the scene. */
    @SerialName("background_color") val backgroundColor: String? = null,
)

/** The screen's weekly power window — same day bitmask (bit 0 = Monday) and `HH:MM` local
 *  times as the CMS stores. See `power/PowerPlan.kt` for how it's evaluated. */
@Serializable
data class PowerSchedule(
    val enabled: Boolean = false,
    @SerialName("days_of_week") val daysOfWeek: Int = 0b1111111,
    @SerialName("power_on") val powerOn: String = "08:00",
    @SerialName("power_off") val powerOff: String = "22:00",
)

/** "Turn on/off now" from the CMS. [until] is an ISO-8601 UTC instant, or null for no end —
 *  which only counts while there is no schedule. See `power/PowerPlan.kt`. */
@Serializable
data class PowerOverride(
    val state: String,
    val until: String? = null,
)

/**
 * Remotely-configured values from the CMS's device-settings registry (backend
 * `services/device_settings.py`). Typed fields for what this build knows how to apply; any key
 * a newer CMS adds is dropped by `ignoreUnknownKeys` on the shared
 * [kotlinx.serialization.json.Json] instance until a field is added here.
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
    /** True swallows every touch on the player, the exit gesture included — see
     *  `MainActivity.dispatchTouchEvent`. Null (never set) means touch works. The way back is
     *  the CMS toggle, or a keyboard's Menu key for the debug overlay. */
    @SerialName("touchscreen_disabled") val touchscreenDisabled: Boolean? = null,
    /** Power is decided on the screen from these two together — see `power/PowerPlan.kt`.
     *  (The older `power_on` manual switch is retired; the CMS no longer sends it.) */
    @SerialName("power_schedule") val powerSchedule: PowerSchedule? = null,
    @SerialName("power_override") val powerOverride: PowerOverride? = null,
)

@Serializable
data class Manifest(
    val version: String,
    val device: ManifestDevice,
    /** null is a valid state — a newly paired screen with nothing assigned yet. */
    val playlist: ManifestPlaylist? = null,
    val items: List<ManifestItem> = emptyList(),
    /** The real, unflattened shape — one or more layered elements per slot. Rides alongside
     *  [items] rather than replacing it (see backend `ManifestResponse.slots`'s own docstring):
     *  an older player simply never reads this field. Empty, not missing, when the backend
     *  predates it or a slot genuinely has no elements — [PlayerEngine] falls back to treating
     *  [items] as one-element slots whenever this is empty. */
    val slots: List<ManifestSlot> = emptyList(),
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
    /** Live control (CMS Live Control page): the one slot to show and hold instead of looping
     *  — always one of [slots]' ids. Null, the usual case, means play the loop. Defaulted for
     *  the same version-skew reason as everything above. */
    @SerialName("live_slot_id") val liveSlotId: String? = null,
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
    /** What the screen's settings actually are right now, read straight from the system
     *  (`DeviceSettingsApplier.currentSettings`) — distinct from [ManifestSettings], which is
     *  what the CMS wants them to be. Primitives of any kind: volume/brightness are numbers,
     *  `power_state` is "on"/"off". */
    @SerialName("reported_settings") val reportedSettings: Map<String, kotlinx.serialization.json.JsonPrimitive>? = null,
    /** How playback is going — see [PlaybackReport]. */
    val playback: PlaybackReport? = null,
    /** Whether this app is Device Owner — the line between a screen the CMS can update and
     *  switch off by itself and one that needs a person for that. The CMS says which. */
    @SerialName("device_owner") val deviceOwner: Boolean? = null,
)

/** Playback health, once per heartbeat: what the CMS shows as "is this box coping?". */
@Serializable
data class PlaybackReport(
    /** Frames the video decoder dropped since the previous heartbeat. */
    @SerialName("dropped_frames") val droppedFrames: Int = 0,
    /** The hardware decoder in use, e.g. "OMX.amlogic.avc.decoder.awesome". */
    val decoder: String? = null,
    /** Measured over the last media download large enough to measure. */
    @SerialName("download_bytes_per_second") val downloadBytesPerSecond: Long? = null,
)

@Serializable
data class UpdateInfo(
    val version: String,
    val url: String,
    /** The APK's size, when the server knows it — a real percentage while downloading, the
     *  offset to resume a partial download from, and a check that the whole file arrived
     *  before it is handed to the installer. */
    val bytes: Long? = null,
    /** When this offer was made (ISO-8601). Part of the offer's identity for backoff: the
     *  same version re-issued from the CMS ("Retry now") carries a new time and is tried at
     *  once, while the unchanged offer seen on every heartbeat after a failure waits out the
     *  cooldown. See `PlayerEngine.maybeSelfUpdate`. */
    @SerialName("requested_at") val requestedAt: String? = null,
)

/**
 * What this screen tells the CMS about an install as it goes — `POST /device/update-status`.
 * Before this existed the whole lifecycle lived in the debug overlay and logcat, and the CMS
 * could only ever say "pending" until the version happened to change.
 */
@Serializable
data class UpdateStatusReport(
    val version: String,
    /** "downloading", "installing" or "failed". Success is never reported: installing kills
     *  this process, and the next heartbeat's `app_version` is the proof. */
    val state: String,
    @SerialName("progress_pct") val progressPct: Int? = null,
    /** In words meant for the operator: "not enough free space", "download timed out". */
    val detail: String? = null,
)

@Serializable
data class HeartbeatResponse(
    val version: String,
    /** Non-null when the server has published a build this screen isn't running. */
    val update: UpdateInfo? = null,
)
