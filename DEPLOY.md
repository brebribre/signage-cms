# Deploy — Fortu CMS

Two Railway services in one project (`fortu-cms`), plus a managed Postgres and a
Cloudflare R2 bucket. Auto-deploy on push to `main`, connected through the dashboard's
Settings → Source flow — connecting a source any other way (e.g. `railway config apply`)
registers no GitHub webhook, and the service silently stops redeploying on push.

## Services

| Service | Root directory | What it runs | Public URL |
|---|---|---|---|
| `backend` | `backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (via `backend/railpack.json`) | `https://signage-cms-production.up.railway.app` |
| `frontend` | `frontend` | `node server.mjs` (`npm run build` at build time) | `https://practical-benevolence-production-b7b2.up.railway.app` |
| `Postgres` | — | `ghcr.io/railwayapp-templates/postgres-ssl:18` | private only |

`frontend`'s `server.mjs` does two things: serves the built SPA, and reverse-proxies `/api/*`
to `backend` server-to-server. See "Why the frontend proxies the API" below — this is not
incidental, it's what makes the session cookie work in every browser.

**Public URLs still say `signage-cms-production`/`practical-benevolence-production` — those
are Railway-assigned slugs from when the services were created without `--service <name>`,
and renaming a service (Settings → General, dashboard-only) does not change its public
domain.** The services are named `backend`/`frontend` everywhere that matters (CLI, this
doc); the URLs are cosmetic history.

Reaching either service by name from the CLI:

```bash
railway service link backend          # or: frontend, Postgres
```

## Why the frontend proxies the API

The two services sit on different `*.up.railway.app` subdomains. `up.railway.app` is
registered on the public suffix list, so these subdomains are **cross-site** to a browser
despite sharing `railway.app` — the session cookie is a cross-site cookie no matter what
`SameSite`/`Secure` say.

The original approach was `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`, which is the
spec-correct way to make a cross-site cookie work — and it did, verified live (see the
Checkpoint below). What that verification missed: `SameSite=None; Secure` is a **courtesy a
browser can still decline**. Arc blocks it regardless — confirmed in production, every
mutating request (`POST /media/uploads`, `POST /playlists`, unrelated to each other except
both needing the cookie) failed with 401 from a real user's phone, despite the config being
exactly what the spec asks for. Safari's ITP and Brave apply similar cross-site cookie
restrictions on their own timelines; there was no reason to expect Arc to be the last one.

The fix that doesn't depend on any particular browser's leniency: stop the cookie from ever
being cross-site. `frontend`'s `server.mjs` proxies `/api/*` to `backend`
**server-to-server** — the browser only ever talks to `frontend`, one origin, for
everything. The backend's `Set-Cookie` (no explicit `Domain` attribute, so it host-scopes to
whoever actually returned it) arrives at the browser looking exactly like a normal first-party
cookie, because as far as the browser can tell, it is one. `SameSite=Lax` — the ordinary,
default-safe value — is enough once this is in place; `None` is no longer required. See
`frontend/server.mjs`'s module docstring for the mechanics.

A **custom domain remains worth doing later** for an unrelated reason: the Android player
bakes in the API host it was provisioned with, and moving that afterward means revisiting
every paired screen — see "Custom domain" below. It is no longer needed to fix cookies.

## Environment variables (backend — `backend`)

Set with `railway variables --service backend --set 'KEY=value'`, or via the dashboard.
Never pasted into chat or committed — see `backend/.env.example` for the full documented list
of names. The ones that matter for *this* deploy, beyond local defaults:

| Variable | Value here | Why it isn't the local default |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | A **reference variable**, not a pasted string — it re-resolves automatically if the Postgres service is ever recreated. A literal connection string here would go stale silently on the next Postgres redeploy. |
| `SECRET_KEY` | a real 64-char value | Generated once with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Rotating it invalidates every existing session — see the runbook below. |
| `COOKIE_SECURE` | `true` | Still required — the cookie must only ever be sent over HTTPS, cross-site or not. |
| `COOKIE_SAMESITE` | `lax` | No longer needs to be `none` — see "Why the frontend proxies the API" above. If this still reads `none` on the live service, it's harmless (a same-site cookie marked `None` still works), but `lax` is the more correct, slightly more CSRF-resistant value now that the browser sees this as a same-site cookie. |
| `FRONTEND_ORIGIN` | `https://practical-benevolence-production-b7b2.up.railway.app` | Governs CORS for anything that calls the backend directly rather than through the proxy — local dev, and any future non-browser client. No longer in the critical path for the deployed CMS's own session cookie. |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | set, not shown | Object Read & Write only, scoped to `fortu-cms`. Deliberately **not** an Admin token — see the R2 CORS section below for what that costs. |
| `LOG_LEVEL` | `INFO` | `DEBUG` locally is too noisy for production logs. |

## Environment variables (frontend — `frontend`)

| Variable | Value here | Why |
|---|---|---|
| `BACKEND_URL` | `https://signage-cms-production.up.railway.app` | Read by `server.mjs` **at runtime** — where it proxies `/api/*` to. Not a `VITE_` variable: those are baked into the client bundle at *build* time and are unreachable from this server-side process. Unset locally, it falls back to `http://localhost:8001`. |

`frontend/.env.production` (committed — no secrets in it) bakes `VITE_API_BASE_URL=/api` into
the build at compile time — the client always calls its own origin, relatively, and never
knows the backend's real address at all. A redeploy is required after changing anything in
it — editing it alone does nothing to an already-built `dist/`.

## The two CORS surfaces

Two entirely separate systems both need the frontend's origin, and fixing one does nothing for
the other:

1. **The backend's own CORS** (`FRONTEND_ORIGIN` above) — governs whether the browser may call
   `signage-cms-production...` from a page served by `practical-benevolence-production...`.
   The deployed CMS itself no longer depends on this (its own calls go through the same-origin
   proxy and never leave `frontend`'s origin) — this still matters for local dev
   (`localhost:5173` calling `localhost:8001` directly) and any other client that calls the
   backend straight.
2. **The R2 bucket's CORS policy** — governs whether the browser may `PUT`/`GET` objects
   directly against Cloudflare, which uploads do without ever touching the backend. Set at
   **R2 → `fortu-cms` → Settings → CORS Policy**:
   ```json
   [{
     "AllowedOrigins": [
       "http://localhost:5173",
       "http://127.0.0.1:5173",
       "https://practical-benevolence-production-b7b2.up.railway.app"
     ],
     "AllowedMethods": ["PUT", "GET", "HEAD"],
     "AllowedHeaders": ["Content-Type"],
     "ExposeHeaders": ["ETag"],
     "MaxAgeSeconds": 3600
   }]
   ```
   **This cannot be set from the backend's own R2 credentials.** The Object Read & Write token
   the backend uses is deliberately scoped too narrowly to manage bucket config —
   `get_bucket_cors`/`put_bucket_cors` both return `AccessDenied` with it, confirmed while
   setting this up. That's the correct trade: broadening the backend's token to Admin just to
   automate a one-time config change would weaken it for no lasting benefit. This box stays a
   manual dashboard edit.

## Custom domain

Not set up yet — both services are on their Railway-assigned `*.up.railway.app` URLs. **Do this
before any real device is paired**: the Android player stores the API base URL it was
provisioned with, and moving the domain afterwards means revisiting every paired screen. This
is no longer needed to fix the session cookie (see "Why the frontend proxies the API" above) —
it's purely about not having to re-provision every screen later.

## Rotating the R2 key

1. Cloudflare dashboard → create a **new** Object Read & Write token scoped to `fortu-cms`
   (same steps as the original — see `CONCRETE_PROJECT_STEPS.md` Phase 0).
2. `railway variables --service backend --set 'R2_ACCESS_KEY_ID=...' --set 'R2_SECRET_ACCESS_KEY=...'`
   — this alone does **not** deploy; the running process keeps the old credentials until
   restarted (see the gotcha below).
3. `railway redeploy --service backend -y` to actually apply it.
4. Confirm `GET /health` still returns `200` and a fresh upload succeeds, then delete the old
   token in Cloudflare.

## Rotating `SECRET_KEY`

Every existing session cookie is signed with the old key and becomes unreadable the instant this
changes — every signed-in user is logged out simultaneously. There is no graceful rollover
without running two keys in parallel, which isn't built. Do this during a low-traffic window,
and only when there's a real reason to (a suspected leak, not routine hygiene).

## A gotcha that cost real time setting this up

**`railway variables --skip-deploys` means exactly what it says: the change sits on the service
but does not reach the running container.** `railway restart` does not fix this either — it
restarts the *existing* deployment, which keeps whatever variable snapshot it already started
with. Only `railway redeploy` (or letting a normal variable-set trigger its automatic redeploy,
i.e. not passing `--skip-deploys`) actually applies a changed variable. Symptom when this bites:
`curl` and the browser both show the *old* config working and the *new* one silently not, even
though `railway variables` reports the new value has been "set." Always follow a
`--skip-deploys` variable change with an explicit `redeploy` before trusting it.

## Checkpoint

Verified live, in an actual browser, against production: signed up on
`practical-benevolence-production...`, the session cookie survived a full page reload (proving
the cross-site `SameSite=None` + `Secure` configuration actually works, not just that CORS
headers look right), and `GET /health` / a CORS preflight both succeed from the real frontend
origin.

**Not yet verified**: a file upload from the deployed frontend (blocked until the R2 CORS policy
above is saved — the backend-side upload pipeline itself is proven in Phase 5/6) and pairing a
device from outside this network. Both are one-time manual steps away from being checkable.

### Incident: Arc browser, 2026-09-11

A real user on Arc got "Not authenticated" on every mutating request (media upload, playlist
creation) despite being signed in. Root cause: the `SameSite=None; Secure` cross-site cookie
setup above, though spec-correct and verified working in the checkpoint, is a courtesy some
browsers decline — Arc blocked it outright. Fixed by making the frontend proxy `/api/*`
server-to-server instead of relying on any browser's cross-site cookie policy — see "Why the
frontend proxies the API" above. `COOKIE_SAMESITE` should be moved from `none` to `lax` on the
live service as part of rolling this out (harmless either way, but `lax` is the honest value
for what the cookie now actually is).

## Still outstanding (dashboard-only, cannot be scripted from here)

- **Railway Postgres backup schedule** — confirm it's on in the dashboard (Postgres service →
  Settings). Not exposed through the CLI.
- **R2 object versioning** on `fortu-cms` — also `AccessDenied` with the Object-scoped token,
  same reasoning as CORS above. A media library is the one thing here that can't be rebuilt
  from code if a delete goes wrong.
- **Custom domain**, if wanted — see above.
