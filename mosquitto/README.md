# MQTT broker

The push-notification broker (`player/PlayerEngine.kt`'s `PushClient`, `backend/app/infra/mqtt.py`).
Deployed as its own Railway service, `mqtt-broker`, in the `pleasing-friendship` project —
not part of the `backend` service, and not connected to GitHub auto-deploy. Changes here
only take effect after you run `railway up` yourself (see **Deploying a change** below).

Not the source of truth for anything. A screen that never receives a push still gets the
same manifest on its next 30s poll — see `PlayerEngine.kt`'s `PushClient` doc comment. Every
procedure below can be done wrong without taking a single screen offline.

## What's actually running

- **TLS only, port 8883.** Self-signed cert (`certs/server.crt`/`server.key`), because the
  broker's hostname is a Railway-owned `*.proxy.rlwy.net` subdomain nothing here controls
  DNS for, so no ACME challenge (HTTP-01 or DNS-01) can ever be completed for it. Both the
  backend (`backend/app/infra/mqtt_ca.pem`) and the Android client
  (`player/.../push/MqttPushClient.kt`'s `MQTT_CA_PEM` constant) pin this exact certificate
  as their trusted root instead of relying on a public CA chain.
- **Per-device credentials** via Mosquitto's dynamic-security plugin
  (`dynamic-security.json`), not one shared password. Two roles:
  - `publisher-role` — the CMS backend's own `cms` client. Full publish on `devices/#`.
  - `device-role` — every paired screen. Subscribe only, scoped to `devices/%u/manifest`
    (`%u` = the connecting client's own username) — a device is broker-level incapable of
    reading another device's topic, not just discouraged from it.
  - Devices are never in the seed file. The backend `createClient`s them live, at pairing
    time, via `backend/app/infra/mqtt_admin.py`.
- **A Railway volume** at `/mosquitto/data`, holding `dynamic-security.json` (live
  client/role state) and the retained-message store. This is what makes a provisioned
  device survive a broker redeploy.

## Two gotchas that cost real debugging time — read before touching the Dockerfile or mqtt_admin.py

1. **A volume mount hides whatever the image put at that path — it does not merge.**
   `Dockerfile` copies the seed file to `/mosquitto/dynamic-security-seed.json`, *not*
   straight to `/mosquitto/data/dynamic-security.json` — a Dockerfile `COPY` to a path a
   volume later mounts is invisible to the running container. Confirmed live: with the seed
   copied directly to the volume path, mosquitto logged *"Dynamic security plugin config
   not found, generating a default config"* and silently minted its own admin with a
   password nobody has. `entrypoint.sh` copies the seed in at container start instead, and
   only if the volume is genuinely still empty — so it never clobbers live device state on
   a redeploy.

2. **dynsec's `createClient -i clientid` is a hard CONNECT-time binding, not a label.** A
   client created with one is refused ("Connection Refused: not authorised") from any MQTT
   client id but that exact string — and the dynsec command itself reports success
   regardless, because from the broker's side nothing is wrong. `mqtt_admin.py`'s
   `provision_device` deliberately does not set it, because Android connects with a random
   `player-${UUID}` id every session, never the device id. If you ever add a `clientid` back
   in here "for clarity," you will lock every device out of its own credential and the API
   will not tell you.

## Rotating the TLS certificate

Needed if the private key leaks, or every ~10 years (current cert's validity).

```bash
cd mosquitto/certs
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 3650 -nodes \
  -subj "/CN=altaria.proxy.rlwy.net" \
  -addext "subjectAltName=DNS:altaria.proxy.rlwy.net"
```

Then update all three places that pin the *old* cert, in the same commit:
- `backend/app/infra/mqtt_ca.pem` — replace with the new `certs/server.crt` verbatim.
- `player/app/src/main/java/com/fortu/player/push/MqttPushClient.kt` — replace the
  `MQTT_CA_PEM` constant's contents with the new cert.
- Redeploy the broker (below) so it actually serves the new cert.

Every already-paired screen and the backend will fail to connect between "broker redeployed
with the new cert" and "that screen/backend gets the new pinned copy" — there's no overlap
window, because a self-signed cert has no intermediate trust to fall back to. Ship the
backend's copy and redeploy the broker together; screens catch up whenever they're next
rebuilt (push is optional, so an old screen just reverts to poll-only in the meantime, not
broken).

## Resetting the admin identity

If `MQTT_ADMIN_PASSWORD` (Railway variable on `backend`) is lost, there's no "reset
password" for it — `dynamic-security.json` only exists inside
the live volume, and the seed file is only consulted on a genuinely empty volume. Recovery
means deleting and recreating the volume (`railway volume delete` / `railway volume add
--mount-path /mosquitto/data`, both against the `mqtt-broker` service), regenerating a fresh
`dynamic-security.json` locally the same way this repo's copy was built (`mosquitto_ctrl
dynsec init`, then `createRole`/`addRoleACL` for `device-role` and `publisher-role`, then
`createClient cms` with the *existing* `MQTT_PASSWORD` so the backend doesn't also need a
new one), and redeploying. **This deletes every currently-provisioned device's credential**
— every paired screen falls back to poll-only until it's unpaired and re-paired. Don't do
this casually.

## Deploying a change

```bash
cd mosquitto
railway service mqtt-broker   # only if some other service is currently linked
railway up . --path-as-root --service mqtt-broker -y --ci
```

Not connected to GitHub — a `git push` alone does nothing here. `railway logs` afterward
should show TLS/dynsec loading with no `"generating a default config"` line; if that line
appears, the volume was empty and just got re-seeded from scratch, which means every
previously-provisioned device needs to re-pair.
