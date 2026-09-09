#!/bin/sh
set -e

# Seed the dynamic-security store on its very first boot only. /mosquitto/data is a Railway
# volume — persistent across redeploys, and mounted *over* whatever this image put there, so
# a plain Dockerfile COPY to that path is invisible the moment a volume exists (confirmed
# live: the plugin logged "config not found, generating a default config" despite the seed
# file being baked in). Copying it here, at container start, is the only point where both the
# image's seed file and the volume's real (possibly already-populated) state are visible at
# once.
if [ ! -f /mosquitto/data/dynamic-security.json ]; then
    cp /mosquitto/dynamic-security-seed.json /mosquitto/data/dynamic-security.json
fi

# The TLS private key is deliberately not in the image (see Dockerfile) — it's written here
# from a Railway variable instead, so it never has to exist in git or a build context. Fail
# loudly rather than let mosquitto start plaintext-only or crash with a confusing bind error.
if [ -z "$MQTT_TLS_KEY_PEM" ]; then
    echo "FATAL: MQTT_TLS_KEY_PEM is not set — mosquitto needs it to serve TLS on 8883." >&2
    exit 1
fi
printf '%s\n' "$MQTT_TLS_KEY_PEM" > /mosquitto/config/certs/server.key
chown mosquitto:mosquitto /mosquitto/config/certs/server.key
chmod 600 /mosquitto/config/certs/server.key

exec /docker-entrypoint.sh "$@"
