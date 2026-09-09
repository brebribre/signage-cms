"""Push notifications to paired screens — the only module that touches paho-mqtt.

Prototype for cutting the manifest-change latency below the 30s poll interval (see
player/PlayerEngine.kt's poll loop): instead of a screen finding out on its next scheduled
check, the CMS publishes a "wake up and look" the moment something actually changes.

This is deliberately a courtesy nudge, not a channel of record. A screen that misses a
publish — offline, a dropped broker connection, MQTT disabled entirely — still catches up on
its next poll, because the manifest endpoint and its ETag remain the one source of truth.
That is what makes every publish here safe to fire-and-forget: it never blocks the caller,
and it can never fail a request that would otherwise have succeeded.

TLS against the deployed broker uses `mqtt_ca.pem`, a self-signed certificate, not one from
a public CA — the broker's hostname is a Railway-owned subdomain (*.proxy.rlwy.net) that
nothing here controls DNS for, so no ACME challenge can be completed for it. Pinning this
exact certificate as the trusted root (instead of the public CA chain) still gets real
encryption and real protection against a network-path attacker; the Android client pins the
same file. Rotating it means updating both.
"""

import logging
import threading
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt_client
import paho.mqtt.publish as mqtt_publish

from app.config import get_settings

logger = logging.getLogger(__name__)

_CA_CERT_PATH = Path(__file__).parent / "mqtt_ca.pem"
_HEALTH_CHECK_TIMEOUT_SECONDS = 3


def _topic(device_id: uuid.UUID) -> str:
    # Keyed by device id alone, not account id: the device itself only ever learns its own
    # id (from the pairing response) and never its account — every HTTP call it makes
    # authenticates by bearer token, so it has no other identifier to subscribe with. A real
    # deployment would isolate topics with per-device broker ACLs instead of a path segment.
    return f"devices/{device_id}/manifest"


def _publish(topic: str, payload: str) -> None:
    settings = get_settings()
    auth = (
        {"username": settings.mqtt_username, "password": settings.mqtt_password}
        if settings.mqtt_username
        else None
    )
    tls = {"ca_certs": str(_CA_CERT_PATH)} if settings.mqtt_tls else None
    try:
        mqtt_publish.single(
            topic,
            payload=payload,
            qos=1,
            # Retained: a screen that was offline when this fired gets the current version
            # the instant it reconnects and subscribes, rather than needing a poll to notice.
            retain=True,
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            auth=auth,
            tls=tls,
            client_id=f"cms-{uuid.uuid4().hex[:8]}",
        )
    except Exception:
        # Never let a broker outage or a wrong host surface as a failed CMS request — see the
        # module docstring. Logged at debug, not warning: with no broker deployed anywhere
        # near production yet, this is the expected steady state until that changes.
        logger.debug("mqtt publish to %s failed (device still catches up on its next poll)",
                     topic, exc_info=True)


def check_connection() -> bool:
    """A real network-and-auth round trip against the broker — used by GET /health to
    answer "is push actually reaching devices right now", which the app process being up
    and Postgres answering cannot tell you on their own.

    Deliberately just a CONNECT, no publish: a CONNACK alone already proves the network
    path, TLS chain and the `cms` credential all work, and doing it this way means a
    health check run every few seconds by an uptime monitor never touches a real device's
    retained topic.

    Returns False whenever MQTT is disabled entirely, exactly like a broker that failed to
    connect — /health.py decides what that should mean for the response, not this.
    """
    settings = get_settings()
    if not settings.mqtt_enabled:
        return False

    connected = threading.Event()
    result = {"ok": False}

    def on_connect(client, userdata, flags, rc, properties=None):
        result["ok"] = rc == 0
        connected.set()

    client = mqtt_client.Client(client_id=f"cms-health-{uuid.uuid4().hex[:8]}")
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=str(_CA_CERT_PATH))
    client.on_connect = on_connect

    try:
        client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=10)
        client.loop_start()
        connected.wait(_HEALTH_CHECK_TIMEOUT_SECONDS)
    except Exception:
        logger.debug("mqtt health check failed", exc_info=True)
        return False
    finally:
        client.loop_stop()
        client.disconnect()

    return result["ok"]


def notify_manifest_changed(*, device_id: uuid.UUID, version: str) -> None:
    """Tell one screen its manifest may have changed. Fire-and-forget, off the request thread.

    Runs on a background thread rather than inline: even with a short-lived connection, a
    broker that is unreachable can hang in the OS's own TCP connect timeout for far longer
    than any CMS write should ever take. A PATCH must return in milliseconds whether or not
    the broker is there to hear about it.
    """
    settings = get_settings()
    if not settings.mqtt_enabled:
        return
    topic = _topic(device_id)
    threading.Thread(target=_publish, args=(topic, version), daemon=True).start()
