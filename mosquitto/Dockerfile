# Deployed to Railway as its own service, built from this directory only — see
# mosquitto.prod.conf for what's actually running: TLS on 8883, and the dynamic-security
# plugin for per-device credentials (no more one shared password for every screen).
FROM eclipse-mosquitto:2

COPY --chown=mosquitto:mosquitto mosquitto.prod.conf /mosquitto/config/mosquitto.conf
COPY --chown=mosquitto:mosquitto certs/server.crt /mosquitto/config/certs/server.crt

# NOT server.key — that file is gitignored on purpose (a private key has no business in a
# git history, image layer, or anywhere a `docker history`/`git log` could ever surface it).
# entrypoint.sh writes it to this same path at container start, from the MQTT_TLS_KEY_PEM
# Railway variable, so a GitHub-triggered build succeeds with no key in the build context.

# NOT copied straight to /mosquitto/data — that path is a Railway volume, mounted *over*
# whatever the image put there, so entrypoint.sh copies this in at container start instead,
# and only the first time the volume is genuinely empty. Contains only the bootstrap admin
# user, the `cms` publisher, and the two shared roles — no device ever lives in this file;
# devices are createClient'd into the live broker at pairing time.
COPY --chown=mosquitto:mosquitto dynamic-security.json /mosquitto/dynamic-security-seed.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
# Setting ENTRYPOINT in this downstream Dockerfile cleared the base image's inherited CMD
# (confirmed: `docker inspect` showed Cmd: null after adding it) — restated explicitly
# rather than relying on inheritance a second time.
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
