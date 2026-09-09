"""Push notifications to paired screens — the only module that touches paho-mqtt.

Prototype for cutting the manifest-change latency below the 30s poll interval (see
player/PlayerEngine.kt's poll loop): instead of a screen finding out on its next scheduled
check, the CMS publishes a "wake up and look" the moment something actually changes.

This is deliberately a courtesy nudge, not a channel of record. A screen that misses a
publish — offline, a dropped broker connection, MQTT disabled entirely — still catches up on
its next poll, because the manifest endpoint and its ETag remain the one source of truth.
That is what makes every publish here safe to fire-and-forget: it never blocks the caller,
and it can never fail a request that would otherwise have succeeded.
"""

import logging
import threading
import uuid

import paho.mqtt.publish as mqtt_publish

from app.config import get_settings

logger = logging.getLogger(__name__)


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
            client_id=f"cms-{uuid.uuid4().hex[:8]}",
        )
    except Exception:
        # Never let a broker outage or a wrong host surface as a failed CMS request — see the
        # module docstring. Logged at debug, not warning: with no broker deployed anywhere
        # near production yet, this is the expected steady state until that changes.
        logger.debug("mqtt publish to %s failed (device still catches up on its next poll)",
                     topic, exc_info=True)


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
