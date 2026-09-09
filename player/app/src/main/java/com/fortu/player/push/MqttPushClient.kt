package com.fortu.player.push

import android.util.Log
import com.fortu.player.PushClient
import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt3.Mqtt3AsyncClient
import com.hivemq.client.mqtt.mqtt3.Mqtt3Client
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.util.UUID

private const val TAG = "FortuPlayer"

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
) : PushClient {
    private val _signal = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    override val signal: SharedFlow<Unit> = _signal

    private var client: Mqtt3AsyncClient? = null
    private var connectedDeviceId: String? = null

    override fun connect(deviceId: String) {
        if (host.isBlank()) return // No broker configured — see build.gradle.kts's mqttHost.
        if (connectedDeviceId == deviceId && client != null) return // Already connecting/connected.
        connectedDeviceId = deviceId

        val c = Mqtt3Client.builder()
            .identifier("player-${UUID.randomUUID()}")
            .serverHost(host)
            .serverPort(port)
            .automaticReconnectWithDefaultConfig()
            .buildAsync()
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
                .callback { _signal.tryEmit(Unit) }
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
