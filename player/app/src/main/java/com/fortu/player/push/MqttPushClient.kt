package com.fortu.player.push

import android.util.Log
import com.fortu.player.PushClient
import com.hivemq.client.mqtt.MqttClientSslConfig
import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt3.Mqtt3AsyncClient
import com.hivemq.client.mqtt.mqtt3.Mqtt3Client
import com.hivemq.client.mqtt.mqtt3.Mqtt3ClientBuilder
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.io.ByteArrayInputStream
import java.security.KeyStore
import java.security.cert.CertificateFactory
import java.util.UUID
import javax.net.ssl.TrustManagerFactory

private const val TAG = "FortuPlayer"

/**
 * A self-signed certificate, not one from a public CA: the broker's hostname is a
 * Railway-owned subdomain (*.proxy.rlwy.net) nothing here controls DNS for, so no ACME
 * challenge can be completed for it. Pinned here as the trusted root instead of relying on
 * the public CA chain — real encryption and real protection against a network-path
 * attacker, just via an explicitly trusted cert. The backend publisher pins the identical
 * file (backend/app/infra/mqtt_ca.pem); rotating it means updating both plus
 * mosquitto/certs/server.crt.
 */
private const val MQTT_CA_PEM = """-----BEGIN CERTIFICATE-----
MIIDRjCCAi6gAwIBAgIUDvj7QB/G8isBE8E2PAfB9QPBJrIwDQYJKoZIhvcNAQEL
BQAwITEfMB0GA1UEAwwWYWx0YXJpYS5wcm94eS5ybHd5Lm5ldDAeFw0yNjA5MDkw
NTIyNDhaFw0zNjA5MDYwNTIyNDhaMCExHzAdBgNVBAMMFmFsdGFyaWEucHJveHku
cmx3eS5uZXQwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDJ3JvL8qgv
Rs6JlLq+3HQmrMHpiGWUxiiEGqmJUbLHjz711bqY+An/DuUg6utHBp11k+Cl7wxi
bSnLELzNQKxFhIdkF/snBdllVmDHpzrMArFpExcfP/aN0d8JXvdvZN3WOUAuILc1
9FaZtaXGY/eK1GRlCs7lqbKvcJCXPf2+x3EVz0npG9xo8SvSeNJI18zhpWA+ZzzI
ZwUnw7ZwNUbqwK7i7uSfXy/WkXT93NcwN/JNPubG+1TxfIOkKKKxRSjLuXtQd1/e
0kOUoijP9oZzucpR5CO0BGiTZaLIsxnqqKIhGUPym9E72ONmP67JWWhT+AoTw0Zl
Dpf653ExFQapAgMBAAGjdjB0MB0GA1UdDgQWBBSgVZkkSCYMDMT09DhToa1NYuX5
BjAfBgNVHSMEGDAWgBSgVZkkSCYMDMT09DhToa1NYuX5BjAPBgNVHRMBAf8EBTAD
AQH/MCEGA1UdEQQaMBiCFmFsdGFyaWEucHJveHkucmx3eS5uZXQwDQYJKoZIhvcN
AQELBQADggEBAL7Wv7fAAdBBch1IZZaxpXQsBjlxzdHo3WIOn8MXbwaPqYGbJsNz
bT9nrLH+nLswshuMweRYs0KTbi7m2SUP8hQH+n86clYyE2DjdNsd7piEMf7gRPqD
Z5bdRgXtlVmB+sgQkokS9CrViEA7cYFtT2/SDlVw5cz8+Fqwi2M51k/xnVdcE686
n0p5jt7iDZzV5oHhYe48iHYz+G2dw9MefnQb1029Mj8DgE3nazbQFsB2eX9c9+tI
mhwM0FjQ7ylB7uaYW6J5WuWx6wVjYTrBoUKIMxqoK1beb7i2tyGjKS3ij6NV1ivL
gcwBz9aZgIwXzsuavxhcjXxe5be8Iz4oUwE=
-----END CERTIFICATE-----"""

private fun pinnedTrustManagerFactory(): TrustManagerFactory {
    val cert = CertificateFactory.getInstance("X.509")
        .generateCertificate(ByteArrayInputStream(MQTT_CA_PEM.toByteArray()))
    val keyStore = KeyStore.getInstance(KeyStore.getDefaultType()).apply {
        load(null, null)
        setCertificateEntry("mqtt-ca", cert)
    }
    return TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()).apply {
        init(keyStore)
    }
}

/**
 * The [PushClient] this app actually ships, backed by [HiveMQ's MQTT client]
 * (pure Kotlin/Java, no bound Android Service the way the old Eclipse Paho Android artifact
 * needed). Talks to the CMS's prototype publisher — see backend/app/infra/mqtt.py — on
 * `devices/{deviceId}/manifest`.
 *
 * Every failure mode here degrades to "just use the normal poll," never to a crash or a
 * blocked screen: a blank [host] means no broker is configured at all (production today), a
 * connect failure means one is configured but unreachable (captive portal, firewalled venue
 * wifi), and either way [PlayerEngine] already treats [signal] as optional. Automatic
 * reconnect is left to the client library's own backoff rather than reimplemented here.
 */
class MqttPushClient(
    private val host: String,
    private val port: Int,
    /** True for the deployed broker, false for local dev's plaintext docker-compose one. */
    private val tls: Boolean = false,
) : PushClient {
    private val _signal = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    override val signal: SharedFlow<Unit> = _signal

    private var client: Mqtt3AsyncClient? = null
    private var connectedDeviceId: String? = null

    /**
     * [deviceId] is also this connection's username — the broker's `device-role` scopes
     * subscribe access to `devices/{username}/manifest`, so there is nothing else a
     * username could mean here. [password] is blank against local dev's anonymous
     * docker-compose broker; the deployed one (mosquitto/, on Railway) requires it —
     * see mosquitto.prod.conf's dynamic-security setup.
     */
    override fun connect(deviceId: String, password: String) {
        if (host.isBlank()) return // No broker configured — see build.gradle.kts's mqttHost.
        if (connectedDeviceId == deviceId && client != null) return // Already connecting/connected.
        connectedDeviceId = deviceId

        var builder: Mqtt3ClientBuilder = Mqtt3Client.builder()
            .identifier("player-${UUID.randomUUID()}")
            .serverHost(host)
            .serverPort(port)
            .automaticReconnectWithDefaultConfig()
        if (tls) {
            builder = builder.sslConfig(
                MqttClientSslConfig.builder()
                    .trustManagerFactory(pinnedTrustManagerFactory())
                    .build()
            )
        }
        if (password.isNotBlank()) {
            builder = builder.simpleAuth()
                .username(deviceId)
                .password(password.toByteArray())
                .applySimpleAuth()
        }
        val c = builder.buildAsync()
        client = c

        c.connect().whenComplete { _, error ->
            if (error != null) {
                // The client's own automatic-reconnect config keeps retrying in the
                // background; nothing further to do here but say why, once, at the level
                // that matches "this is an optimization, not a failure."
                Log.i(TAG, "mqtt connect failed for now — polling continues as normal", error)
                return@whenComplete
            }
            c.subscribeWith()
                .topicFilter("devices/$deviceId/manifest")
                .qos(MqttQos.AT_LEAST_ONCE)
                .callback { publish ->
                    Log.i(TAG, "mqtt: push received, version ${publish.payloadAsBytes.toString(Charsets.UTF_8)}")
                    _signal.tryEmit(Unit)
                }
                .send()
                .whenComplete { _, subError ->
                    if (subError != null) {
                        Log.w(TAG, "mqtt subscribe failed", subError)
                    } else {
                        Log.i(TAG, "mqtt: listening for pushes on device $deviceId")
                    }
                }
        }
    }

    override fun disconnect() {
        client?.disconnect()
        client = null
        connectedDeviceId = null
    }
}
