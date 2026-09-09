# MQTT broker

The push-notification broker (`player/PlayerEngine.kt`'s `PushClient`, `backend/app/infra/mqtt.py`).
Deployed as its own Railway service, `mqtt-broker`, in the `pleasing-friendship` project —
not part of the `backend` service. Connected to GitHub auto-deploy: a push to `main` that
touches `mosquitto/` redeploys it. Root Directory is set to `/mosquitto` and the build uses
this directory's `Dockerfile` — see **Deploying a change** below if either setting ever
reverts to auto-detect (it has happened once already, see that section).

Not the source of truth for anything. A screen that never receives a push still gets the
same manifest on its next 30s poll — see `PlayerEngine.kt`'s `PushClient` doc comment. Every
procedure below can be done wrong without taking a single screen offline.

## What's actually running

- **TLS only, port 8883.** Self-signed cert (`certs/server.crt`), because the broker's
  hostname is a Railway-owned `*.proxy.rlwy.net` subdomain nothing here controls DNS for, so
  no ACME challenge (HTTP-01 or DNS-01) can ever be completed for it. Both the backend
  (`backend/app/infra/mqtt_ca.pem`) and the Android client
  (`player/.../push/MqttPushClient.kt`'s `MQTT_CA_PEM` constant) pin this exact certificate
  as their trusted root instead of relying on a public CA chain. The private key
  (`certs/server.key`) is gitignored and never enters the Docker image — `entrypoint.sh`
  writes it to `/mosquitto/config/certs/server.key` at container start, from the
  `MQTT_TLS_KEY_PEM` Railway variable on this service.
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

3. **Connecting (or reconnecting) this service to a GitHub repo resets its Root Directory
   and Builder to auto-detect, and GitHub source paths are relative (no leading slash) —
   not absolute like CLI upload paths.** Confirmed live, two failures in sequence:
   - Right after connecting GitHub, a redeploy failed with `railpack prepare exited with an
     error` — Railway had reset the build to auto-detect instead of Dockerfile.
   - Setting `rootDirectory: "/mosquitto"` and `dockerfilePath: "/Dockerfile"` (the same
     leading-slash form the old CLI `--path-as-root` flow used) got further, but then failed
     instantly with *"Root directory '/mosquitto' was not found in the deployed source"* —
     even though `mosquitto/` genuinely exists at the tip of `main`. GitHub source
     resolution wants paths **relative to the repo root, no leading slash**:
     `rootDirectory: "mosquitto"`, `dockerfilePath: "Dockerfile"`. That's what's set now and
     what a working deploy actually used.

   There's no CLI or dashboard toggle for either field — both are set via the Railway API's
   `serviceInstanceUpdate` mutation:
   ```bash
   railway api 'mutation($serviceId:String!,$environmentId:String,$input:ServiceInstanceUpdateInput!){serviceInstanceUpdate(serviceId:$serviceId,environmentId:$environmentId,input:$input)}' \
     --raw-var serviceId=<mqtt-broker service ID> --raw-var environmentId=<production environment ID> \
     --variables '{"input":{"rootDirectory":"mosquitto","dockerfilePath":"Dockerfile"}}'
   ```
   (The `builder` field itself only accepts `RAILPACK`/`NIXPACKS`/`PAKETO`/`HEROKU` in the
   public schema — there's no `DOCKERFILE` literal to set directly. Setting `dockerfilePath`
   to a non-null value is what actually flips the effective build to Dockerfile.)

   If a future GitHub reconnect breaks the build again, that's almost certainly why. Check
   `railway logs --build --latest --service mqtt-broker`: `railpack prepare exited with an
   error` means Root Directory/Builder got reset; a build that fails within a few seconds
   with no build-step log lines at all (check `railway api` on the deployment directly, since
   this particular error doesn't appear in `railway logs` output) means Root Directory has
   the wrong path format.

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

And update the private key Railway holds, since it's never in git or the image:
```bash
railway variable set MQTT_TLS_KEY_PEM --stdin --service mqtt-broker --skip-deploys \
  < mosquitto/certs/server.key
```

Then redeploy the broker (below) so it actually serves the new cert and key together.

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

Push to `main` with changes under `mosquitto/` — GitHub auto-deploy picks it up. To deploy
without waiting on a push (or to redeploy the same commit, e.g. after fixing a Railway
variable), pull the latest commit from source explicitly:

```bash
railway redeploy --service mqtt-broker --from-source -y
```

`railway logs --build --latest --service mqtt-broker` afterward should show the Dockerfile
build steps (`[[N]/7] COPY ...`), not `railpack prepare` — see gotcha 3 above if it doesn't.
Deploy logs should show TLS/dynsec loading with no `"generating a default config"` line; if
that line appears, the volume was empty and just got re-seeded from scratch, which means
every previously-provisioned device needs to re-pair.

Plain CLI upload (`railway up`) no longer works cleanly for this service, now that it has a
persisted Root Directory (`mosquitto`, needed for GitHub builds) — confirmed live, both
directions fail:
- `railway up . --path-as-root --service mqtt-broker` (from `mosquitto/`) — server tries to
  apply Root Directory on top of the already-scoped upload and can't find a `mosquitto/`
  subdirectory inside it.
- `railway up --service mqtt-broker` (from the repo root) — ignores Root Directory entirely
  and looks for `Dockerfile` at the upload root, i.e. the repo root, where it doesn't exist.

To deploy uncommitted local changes for a one-off test, clear Root Directory first, upload,
then restore it:
```bash
railway api 'mutation($serviceId:String!,$environmentId:String,$input:ServiceInstanceUpdateInput!){serviceInstanceUpdate(serviceId:$serviceId,environmentId:$environmentId,input:$input)}' \
  --raw-var serviceId=<mqtt-broker service ID> --raw-var environmentId=<production environment ID> \
  --variables '{"input":{"rootDirectory":""}}'
cd mosquitto && railway up . --path-as-root --service mqtt-broker -y --ci
# then restore rootDirectory: "mosquitto" the same way (no leading slash — see gotcha 3),
# or GitHub builds break again
```
Otherwise, just commit and push — that's the supported path now.
