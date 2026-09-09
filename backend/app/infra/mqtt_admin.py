"""Provisions per-device MQTT credentials on the broker — the fix for every device (and
this backend) having shared one password. See mosquitto/mosquitto.prod.conf for the two
roles this relies on: `device-role` (subscribe only, scoped to the caller's own
`devices/{username}/manifest` via the broker's `%u` substitution) and `publisher-role`
(this backend's own `cms` identity, full publish rights).

Talks to Mosquitto's dynamic-security plugin over its own control protocol: commands are
published as JSON to `$CONTROL/dynamic-security/v1`, responses arrive on
`$CONTROL/dynamic-security/v1/response`. There is no REST API for this — the admin
connection is itself just another MQTT client, authenticated as `admin`.

Deliberately NOT best-effort like infra/mqtt.py's push notifications. A device that pairs
without ever getting real MQTT credentials would silently never receive a push for its
entire lifetime, with nothing visibly wrong — the poll loop hides it completely. So this
raises on failure, and the caller (services/devices.py) decides whether that should fail
pairing outright or just log and move on.
"""

import json
import logging
import secrets
import threading
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

from app.config import get_settings

logger = logging.getLogger(__name__)

_CA_CERT_PATH = Path(__file__).parent / "mqtt_ca.pem"
_CONTROL_TOPIC = "$CONTROL/dynamic-security/v1"
_RESPONSE_TOPIC = "$CONTROL/dynamic-security/v1/response"
_TIMEOUT_SECONDS = 5

_ALREADY_EXISTS = "Client already exists."


class MqttAdminError(Exception):
    pass


def _run_commands(commands: list[dict]) -> list[dict]:
    """One connect–command–disconnect round trip. A fresh connection every call rather
    than a held-open admin client: this runs once per pairing, not per second, and a
    short-lived connection can never be the thing left dangling by a crashed request."""
    settings = get_settings()
    outcome: dict = {"responses": None, "connect_rc": None}
    done = threading.Event()

    client = mqtt.Client(client_id=f"cms-admin-{uuid.uuid4().hex[:8]}")
    client.username_pw_set(settings.mqtt_admin_username, settings.mqtt_admin_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=str(_CA_CERT_PATH))

    def on_connect(c, userdata, flags, rc, properties=None):
        outcome["connect_rc"] = rc
        if rc != 0:
            done.set()
            return
        c.subscribe(_RESPONSE_TOPIC)

    def on_subscribe(c, userdata, mid, granted_qos, properties=None):
        c.publish(_CONTROL_TOPIC, json.dumps({"commands": commands}))

    def on_message(c, userdata, msg):
        outcome["responses"] = json.loads(msg.payload)["responses"]
        done.set()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=10)
    client.loop_start()
    try:
        if not done.wait(_TIMEOUT_SECONDS):
            raise MqttAdminError("broker did not respond to the dynsec admin command in time")
    finally:
        client.loop_stop()
        client.disconnect()

    if outcome["connect_rc"] not in (0, None):
        raise MqttAdminError(f"admin connect failed: rc={outcome['connect_rc']}")
    if outcome["responses"] is None:
        raise MqttAdminError("broker accepted the command but sent no response")
    return outcome["responses"]


def provision_device(device_id: uuid.UUID) -> str | None:
    """This device's own MQTT identity — username is the device id itself (not a secret;
    every device already knows its own id), password is freshly minted here and returned
    to the caller to hand to the device. Never stored: losing it just means the device's
    next re-pair mints a new one, the same way a lost bearer token would.

    Safe to call on an already-provisioned device (re-pairing) — the existing client's
    password is rotated rather than erroring on "already exists", and its role is left
    alone rather than re-added, which the broker answers with an unhelpful "Internal
    error" for no reason other than the role was already there.

    Returns None when no admin identity is configured — deliberately its own check, not
    folded into mqtt_enabled: local dev's docker-compose broker has push notifications on
    (mqtt_enabled) but no dynsec plugin loaded at all, and without this a pairing test
    would sit for the full admin-call timeout on every claim, waiting for a control-topic
    response nothing there will ever send.
    """
    settings = get_settings()
    if not settings.mqtt_admin_username:
        return None

    username = str(device_id)
    password = secrets.token_urlsafe(24)

    created = _run_commands([
        {"command": "createClient", "username": username, "password": password,
         "clientid": username, "textname": f"device {username}"},
    ])[0]

    if created.get("error") == _ALREADY_EXISTS:
        reset = _run_commands([
            {"command": "setClientPassword", "username": username, "password": password},
        ])[0]
        if reset.get("error"):
            raise MqttAdminError(f"setClientPassword: {reset['error']}")
    elif created.get("error"):
        raise MqttAdminError(f"createClient: {created['error']}")
    else:
        added = _run_commands([
            {"command": "addClientRole", "username": username, "rolename": "device-role"},
        ])[0]
        if added.get("error"):
            raise MqttAdminError(f"addClientRole: {added['error']}")

    return password
