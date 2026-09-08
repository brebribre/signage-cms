package com.fortu.player.api

import com.fortu.player.BuildConfig
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Raised when the server rejects our device token — the screen must re-pair. */
class UnauthorizedException : IOException("device token rejected")

/**
 * The two endpoints a paired screen talks to, plus the two it uses to get paired.
 *
 * OkHttp rather than Retrofit: four calls total does not justify the extra layer, and the
 * manifest's conditional GET needs direct header access anyway.
 */
class ApiClient(
    private val baseUrl: String = BuildConfig.API_BASE_URL,
    val http: OkHttpClient = defaultClient(),
) {
    private val json = Json { ignoreUnknownKeys = true }

    companion object {
        fun defaultClient(): OkHttpClient = OkHttpClient.Builder()
            // Generous, because venue wifi is frequently awful and a slow response is far
            // better than a failed one for a screen that is otherwise idle.
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            // Downloads of a few hundred MB over bad wifi must not be killed mid-transfer.
            .callTimeout(0, TimeUnit.MILLISECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    fun startPairing(): PairStartResponse {
        val req = Request.Builder()
            .url("$baseUrl/devices/pair")
            .post(ByteArray(0).toRequestBody())
            .build()
        http.newCall(req).execute().use { res ->
            if (!res.isSuccessful) throw IOException("pair failed: HTTP ${res.code}")
            return json.decodeFromString(res.body!!.string())
        }
    }

    /** Returns null when the pairing has expired or was already collected (HTTP 404). */
    fun pollPairing(pollToken: String): PairPollResponse? {
        val req = Request.Builder().url("$baseUrl/devices/pair/$pollToken").get().build()
        http.newCall(req).execute().use { res ->
            if (res.code == 404) return null
            if (!res.isSuccessful) throw IOException("poll failed: HTTP ${res.code}")
            return json.decodeFromString(res.body!!.string())
        }
    }

    /**
     * `null` means "nothing changed" — the server answered 304 against the ETag we sent.
     * That is the normal case on almost every poll, and it costs a few hundred bytes.
     */
    fun fetchManifest(token: String, etag: String?): Manifest? {
        val builder = Request.Builder()
            .url("$baseUrl/device/manifest")
            .header("Authorization", "Bearer $token")
            .get()
        if (etag != null) builder.header("If-None-Match", etag)

        http.newCall(builder.build()).execute().use { res ->
            if (res.code == 304) return null
            if (res.code == 401) throw UnauthorizedException()
            if (!res.isSuccessful) throw IOException("manifest failed: HTTP ${res.code}")
            return json.decodeFromString(res.body!!.string())
        }
    }

    fun heartbeat(token: String, body: HeartbeatRequest): HeartbeatResponse {
        val req = Request.Builder()
            .url("$baseUrl/device/heartbeat")
            .header("Authorization", "Bearer $token")
            .post(
                json.encodeToString(HeartbeatRequest.serializer(), body)
                    .toRequestBody("application/json".toMediaType())
            )
            .build()
        http.newCall(req).execute().use { res ->
            if (res.code == 401) throw UnauthorizedException()
            if (!res.isSuccessful) throw IOException("heartbeat failed: HTTP ${res.code}")
            return json.decodeFromString(res.body!!.string())
        }
    }
}
