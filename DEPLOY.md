# Deploy — Fortu CMS

Two Railway services in one project (`pleasing-friendship`), plus a managed Postgres and a
Cloudflare R2 bucket. Auto-deploy on push to `main`, connected through the dashboard's
Settings → Source flow — connecting a source any other way (e.g. `railway config apply`)
registers no GitHub webhook, and the service silently stops redeploying on push.

## Services

| Service | Root directory | What it runs | Public URL |
|---|---|---|---|
| `signage-cms` | `backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (via `backend/railpack.json`) | `https://signage-cms-production.up.railway.app` |
| `practical-benevolence` | `frontend` | `serve -s dist -l $PORT` (`npm run build` at build time) | `https://practical-benevolence-production-b7b2.up.railway.app` |
| `Postgres` | — | `ghcr.io/railwayapp-templates/postgres-ssl:18` | private only |

**`practical-benevolence` is the frontend.** The name is a Railway-assigned random slug from
when the service was created without `--service <name>`; renaming it is dashboard-only
(Settings → General) and purely cosmetic — nothing depends on the name.

Reaching either service by name from the CLI:

```bash
railway service link signage-cms          # or: practical-benevolence, Postgres
```

## Environment variables (backend — `signage-cms`)

Set with `railway variables --service signage-cms --set 'KEY=value'`, or via the dashboard.
Never pasted into chat or committed — see `backend/.env.example` for the full documented list
of names. The ones that matter for *this* deploy, beyond local defaults:

| Variable | Value here | Why it isn't the local default |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | A **reference variable**, not a pasted string — it re-resolves automatically if the Postgres service is ever recreated. A literal connection string here would go stale silently on the next Postgres redeploy. |
| `SECRET_KEY` | a real 64-char value | Generated once with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Rotating it invalidates every existing session — see the runbook below. |
| `COOKIE_SECURE` | `true` | Required for `COOKIE_SAMESITE=none` to be honoured at all; browsers ignore `SameSite=None` without `Secure`. |
| `COOKIE_SAMESITE` | `none` | **Required**, not optional, because of the next row. |
| `FRONTEND_ORIGIN` | `https://practical-benevolence-production-b7b2.up.railway.app` | The two services sit on different `*.up.railway.app` subdomains. `up.railway.app` is registered on the public suffix list, so these subdomains are **cross-site** to a browser despite sharing `railway.app` — `SameSite=Lax` silently drops the session cookie between them. This is the single most common way this deploy breaks; see the runbook below if login starts 401-looping. |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | set, not shown | Object Read & Write only, scoped to `fortu-cms`. Deliberately **not** an Admin token — see the R2 CORS section below for what that costs. |
| `LOG_LEVEL` | `INFO` | `DEBUG` locally is too noisy for production logs. |

`frontend/.env.production` (committed — no secrets in it) bakes `VITE_API_BASE_URL` into the
build at compile time, since Vite cannot read Railway's runtime variables from a static bundle.
It must point at the backend's exact public URL, and a redeploy is required after changing it —
editing it alone does nothing to an already-built `dist/`.

## The two CORS surfaces

Two entirely separate systems both need the frontend's origin, and fixing one does nothing for
the other:

1. **The backend's own CORS** (`FRONTEND_ORIGIN` above) — governs whether the browser may call
   `signage-cms-production...` from a page served by `practical-benevolence-production...`.
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
provisioned with, and moving the domain afterwards means revisiting every paired screen. If a
custom domain is added later, putting both services behind subdomains of the *same* apex
(`app.example.com` / `api.example.com`) removes the cross-site cookie problem entirely rather
than requiring `SameSite=None` — worth doing at that point rather than carrying the current
workaround forward indefinitely.

## Rotating the R2 key

1. Cloudflare dashboard → create a **new** Object Read & Write token scoped to `fortu-cms`
   (same steps as the original — see `CONCRETE_PROJECT_STEPS.md` Phase 0).
2. `railway variables --service signage-cms --set 'R2_ACCESS_KEY_ID=...' --set 'R2_SECRET_ACCESS_KEY=...'`
   — this alone does **not** deploy; the running process keeps the old credentials until
   restarted (see the gotcha below).
3. `railway redeploy --service signage-cms -y` to actually apply it.
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

## Still outstanding (dashboard-only, cannot be scripted from here)

- **Railway Postgres backup schedule** — confirm it's on in the dashboard (Postgres service →
  Settings). Not exposed through the CLI.
- **R2 object versioning** on `fortu-cms` — also `AccessDenied` with the Object-scoped token,
  same reasoning as CORS above. A media library is the one thing here that can't be rebuilt
  from code if a delete goes wrong.
- **Custom domain**, if wanted — see above.
