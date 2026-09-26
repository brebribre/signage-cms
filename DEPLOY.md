# Deploy — Fortu CMS

Three app services in one project (`fortu-cms`), plus a managed Postgres and a
Cloudflare R2 bucket. Auto-deploy on push to `main`, connected through the dashboard's
Settings → Source flow — connecting a source any other way (e.g. `railway config apply`)
registers no GitHub webhook, and the service silently stops redeploying on push.

## Services

| Service | Root directory | What it runs | Public URL |
|---|---|---|---|
| `backend` | `backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (via `backend/railpack.json`) | `https://api.marien.co.id` |
| `frontend` | `frontend` | `node server.mjs` (`npm run build` at build time) | `https://app.marien.co.id` |
| `web-player` | `web-player` | `node server.mjs` (`npm run build` at build time) — the browser player for smart TVs, see `web-player/README.md` | `https://player.marien.co.id` |
| `monitoring` | `monitoring` | `node server.mjs` (`npm run build` at build time) — Marien staff only: issues customer accounts and their limits. Its own app, deliberately split from the customer-facing `frontend`; sign-in is `/admin/auth/login`, which refuses anyone who isn't staff — the main user of an owner or admin account (`accounts.kind`; see `scripts/set_account_kind.py`). | `https://monitoring-production-69c1.up.railway.app` |
| `Postgres` | — | `ghcr.io/railwayapp-templates/postgres-ssl:18` | private only |

The documentation is **not** a Railway service any more. The guides live in the public repo
`brebribre/paskall-docs` and are published by GitHub Pages at
https://docs.marien.co.id/ — MkDocs, rebuilt on every push there, edited by the team
through the pencil on each page. The CMS sidebar's "Documentation" link points there. The old
hand-written `docs/` folder in this repo and its `docs` Railway service were retired on 2026-09-21.

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
| `FRONTEND_ORIGIN` | `https://app.marien.co.id` | Governs CORS for anything that calls the backend directly rather than through the proxy — local dev, and any future non-browser client. No longer in the critical path for the deployed CMS's own session cookie. |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | set, not shown | Object Read & Write only, scoped to `fortu-cms`. Deliberately **not** an Admin token — see the R2 CORS section below for what that costs. |
| `LOG_LEVEL` | `INFO` | `DEBUG` locally is too noisy for production logs. |

## Environment variables (frontend — `frontend`)

| Variable | Value here | Why |
|---|---|---|
| `BACKEND_URL` | `https://api.marien.co.id` | Read by `server.mjs` **at runtime** — where it proxies `/api/*` to. Not a `VITE_` variable: those are baked into the client bundle at *build* time and are unreachable from this server-side process. Unset locally, it falls back to `http://localhost:8001`. |

`frontend/.env.production` (committed — no secrets in it) bakes `VITE_API_BASE_URL=/api` into
the build at compile time — the client always calls its own origin, relatively, and never
knows the backend's real address at all. A redeploy is required after changing anything in
it — editing it alone does nothing to an already-built `dist/`.

## Environment variables (monitoring — `monitoring`)

| Variable | Value here | Why |
|---|---|---|
| `BACKEND_URL` | `https://api.marien.co.id` | Read by `monitoring/server.mjs` at runtime — where it proxies `/api/*` to, exactly as `frontend` does. The client only ever calls `/api` on its own origin, so the session cookie is first-party and the backend needs no CORS entry for this app. |

No `VITE_` variables: `monitoring/src/api/request.ts` hard-codes `/api`, and in local dev the Vite
server proxies it to `http://localhost:8001` (`monitoring/vite.config.ts`). Locally the app runs
on `127.0.0.1:5176`, not `localhost` — a different host to the CMS on purpose, so signing in and
out of monitoring never touches a CMS session in the same browser.

The service was created from the CLI (`railway add --service monitoring …`) and first deployed
with, from the **repo root**:

```bash
railway up ./monitoring --path-as-root --service monitoring
```

`--path-as-root` matters: without it the CLI archives the whole git repo (even when run from
inside `monitoring/`), the builder finds no `package.json` at the top, and the deploy fails at
once with an empty log. `monitoring/.railwayignore` keeps `node_modules` and `dist` out of the
upload.

The service is now connected to this GitHub repo, branch `main` (`railway service source connect
--repo brebribre/signage-cms --branch main --service monitoring`), so pushes trigger a deploy —
**but it also needs its Root Directory set to `monitoring`, which only the dashboard can do
(Settings → Source → Root Directory); the CLI and the public API's CLI login both refuse it.**
Until that is set, every GitHub-triggered deploy fails the same way the root-archive upload did,
and the last successful deployment keeps serving. Set it once, then Redeploy (or push).

Who can sign in: the main user of an **owner** or **admin** account (`accounts.kind`); the
whole model is written up in [ACCOUNTS.md](ACCOUNTS.md). Owner
issues admin and client accounts and sets limits on both; admin issues client accounts and sets
client limits only; a client never gets in. Admin accounts are issued from the app itself; the
one owner account is set by hand with `backend/scripts/set_account_kind.py --username you --kind
owner`, run inside the backend service — see the "Railway one-off scripts" note in the runbook.
Everyone else gets the same 401 as a wrong password.

## Environment variables (web player — `web-player`)

| Variable | Value here | Why |
|---|---|---|
| `BACKEND_URL` | `https://api.marien.co.id` | Where `server.mjs` proxies `/api/*`, exactly like `frontend`'s. A screen only ever talks to the web player's own origin, so the backend needs no CORS entry for it. |

Created 2026-09-16 with `railway add --service web-player --repo brebribre/signage-cms`, which
does create the GitHub deploy trigger. The root directory is **not** settable with
`railway environment edit` (CLI 5.43–5.57 answer "No changes to apply" to every edit); it was
set through the GraphQL API's `serviceInstanceUpdate(rootDirectory: "/web-player")` — or
Settings → Source → Root directory in the dashboard. A screen reloads itself onto a new deploy
within 5 minutes (it compares `RAILWAY_DEPLOYMENT_ID` from `/version.json`).

**Offline pictures need one more R2 CORS origin** — add
`https://player.marien.co.id` to the bucket policy below (`player.paskall.co.id` from 2026-09-17
until that domain is retired).
Without it web screens stream everything from R2 instead of caching it.

**`backend` needs ffmpeg** — `backend/railpack.json` installs it (`deploy.aptPackages`). The API
process uses it to make each video's streaming copy for web screens
(`app/services/video_streams.py`), on a background thread, right after upload and at startup for
anything still missing one. Without ffmpeg nothing breaks: web screens stream those videos from R2.

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
       "https://app.marien.co.id",
       "https://player.marien.co.id"
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

**marien.co.id** since 2026-09-26 (DNS at Hostinger): the website on the root (an `ALIAS @`
record), `app` (frontend), `api` (backend), `player` (web-player) and `monitoring`, each a
CNAME to the per-service target Railway prints from `railway domain <name> --service <svc>`,
plus the `_railway-verify.<name>` TXT record it asks for; certificates take a while to issue
(about two hours the first time). `docs.marien.co.id` is GitHub Pages (brebribre/paskall-docs,
its `docs/CNAME`). Railway's plan allows two custom domains per service, so the website holds
`marien.co.id` and `www.marien.co.id` only once `paskall.co.id` is gone.

**paskall.co.id is being retired.** It was the domain from 2026-09-22 to 2026-09-26. Android
builds 1.3.8 to 1.4.3 have `https://api.paskall.co.id` compiled in, and builds before 1.3.8 the
backend's `*.up.railway.app` address, so `api.paskall.co.id` stays attached to the backend until
every screen reports 1.4.4 or later (`api.marien.co.id` compiled in); only then remove it and
the other `*.paskall.co.id` domains (`railway domain delete <name> --service <svc>`). A web
player opened at `player.paskall.co.id` keeps its pairing in that origin's storage, so a TV
moved to `player.marien.co.id` pairs again.

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
