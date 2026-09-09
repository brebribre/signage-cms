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

exec /docker-entrypoint.sh "$@"
