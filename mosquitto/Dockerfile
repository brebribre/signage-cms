# Deployed to Railway as its own service, built from this directory only — see
# mosquitto.prod.conf for what's actually running and what it's still missing (TLS).
FROM eclipse-mosquitto:2

COPY --chown=mosquitto:mosquitto mosquitto.prod.conf /mosquitto/config/mosquitto.conf
COPY --chown=mosquitto:mosquitto passwd /mosquitto/config/passwd

# The image's own entrypoint expects to run as its built-in mosquitto user; matches
# docker-compose's local setup so the same image behaves the same way in both places.
