# Signage CMS — Development Step-by-Step

Concrete, ordered build steps. Each phase should be working and testable before moving to the
next, and each ends with a `scripts/check_*.py` that can be re-run later.

Structure follows [brebribre/strava-comp](https://github.com/brebribre/strava-comp): a layered
FastAPI backend (`api → services → infra`) in `/backend`, a Vue 3 + Vite + Tailwind frontend in
`/frontend` with the `View → Container → Hook → API hook` rule, Postgres in `docker-compose.yml`,
Alembic migrations run in the FastAPI lifespan, deployed on Railway.

---

## What we are building

Three things, in this order of dependency:

1. **An account, with users under it** — an owner signs up; the owner creates **subusers**, each
   scoped to a subset of the account's devices. Login is username **or** email, plus a password.
   Media, playlists and devices belong to the *account*, not to the person who created them.
2. **A CMS website** — upload media, arrange it into playlists, register devices, point a device
   at a playlist.
3. **A device runtime** — an **Android** screen that pairs itself to an account, pulls its
   playlist, downloads the files to local storage, and plays them on loop.

The website is Phases 1–10. The player is Phases 12a–12c, and it appears in this plan mainly so the
API it consumes is designed before it is built rather than after.

**Android only, for now.** Windows is not in scope; if it arrives later it is a second player
against an unchanged API, and `player/` becomes `player-android/` beside it.

### Repository layout

```
signage-cms/
  backend/            FastAPI — api → services → infra
  frontend/           the CMS website (Vue 3 + Vite + Tailwind)
  player/             Android app (Gradle project) — Kotlin, Compose, Media3
  docker-compose.yml
```

**The player is a native Android app, not a web page in a WebView.** With one platform to support
there is no shared-logic argument left for the hybrid approach, and Media3 gives the two things
signage actually needs — pre-download with offline playback, and a mixed image/video playlist — as
library features rather than as things to hand-roll. It talks to the backend over the device API in
Phase 10 and shares nothing else with the CMS.

---

## Decisions to confirm before Phase 0

These change the work materially. My recommendation is marked; say the word and the phases below
get rewritten around a different answer.

| # | Decision | Recommendation | Why |
|---|---|---|---|
| 1 | **Where media files live** | ✅ **CONFIRMED** — Cloudflare R2, bucket **`fortu-cms`** | Railway's filesystem is ephemeral. R2 has **no egress fees**, which matters when N screens download the same 200 MB video. `boto3` talks to it unchanged. |
| 2 | **How files get uploaded** | ✅ Browser → storage **directly**, via a presigned `PUT` | A 500 MB video never touches the API, so proxy body limits and request timeouts stop being a concern. |
| 3 | **Who reads image/video metadata** | ✅ The **browser**, at upload time | Avoids an `ffmpeg` dependency in the backend image. `ffprobe` stays the upgrade path. |
| 4 | **How a device gets its content** | ✅ **Polling** a manifest every 30 s with an `ETag` | A screen that updates within 30 s is indistinguishable from instant. A websocket adds a connection to keep alive and debug over flaky venue wifi for no visible gain. |
| 5 | **Login credential** | ✅ **Username or email** + password, argon2, signed HttpOnly session cookie | Subusers are created *by* the owner and often have no email address of their own, so username must be a first-class login. Email stays optional and unique when present. |
| 6 | **Account vs. user** | ✅ An **`accounts` table**; every resource carries `account_id`, not `owner_id` | This is what subusers require. A subuser's upload has to be visible to the owner and to their colleagues, so the library belongs to the account. Hanging resources off a user id and adding `parent_id` looks smaller and breaks the first time an owner deletes a subuser. |
| 7 | **How a subuser is scoped** | ✅ An explicit **`device_access(user_id, device_id)`** grant table | Nothing derived, nothing to keep in sync, one join to enforce. Device *groups* are the right answer at 200 screens and can populate or replace this table later; at 5–50 a checkbox list is better. |
| 8 | **Permission model** | ✅ Two roles: **`owner`** and **`manager`** | One rule to remember: *a manager can do anything an owner can, except manage users, and except touch devices they were not granted.* Media and playlists stay shared account-wide. |
| 9 | **Username uniqueness** | ✅ **Globally unique** | Keeps login to a single field. The cost is that `lobby` is claimable once across all accounts — noted as a known limitation, with per-account namespacing (`acme.lobby`) as the escape hatch if it ever bites. |
| 10 | **Player platform** | ✅ **Native Android** — Kotlin, Compose, Media3 | With one platform there is no shared-logic case for a WebView. Media3 gives pre-download-then-play-offline and mixed image/video playlists as library features. |
| 11 | **Scheduling (dayparting)** | ✅ **Phase 13**, after the loop works | "Device plays playlist" must be boringly reliable before "device plays A 9–5 and B overnight" is worth having. |

Two smaller ones, already assumed below: local Postgres runs on host port **5434** (5433 is
strava-comp's, and both should run at once), and the session cookie is named `scms_session`.

---

## Phase 0: Prerequisites

- [ ] Confirm the remaining decisions above
- [x] **Cloudflare R2 bucket created** — `fortu-cms`, endpoint
      `https://74c0ceb3565715dd70bbe3d4f585412f.r2.cloudflarestorage.com`
- [ ] Create an **R2 API token** — dashboard → **R2 object storage** → *Account Details* →
      **API Tokens** → **Manage** → **Create API token**:
      - **Account API token**, not a User token. A User token dies with the user it belongs to;
        a service credential should not. (Creating one needs the Super Administrator role.)
      - Permission **Object Read & Write** — *not* Admin. Admin can create and delete buckets,
        which the backend never does, and **only Object-level permissions can be scoped to a
        single bucket**.
      - Scope to **`fortu-cms`** only.
      - Copy the **Access Key ID** and **Secret Access Key**. ⚠️ The secret is shown **once**.
        The page also displays a *Token value* — that is for Cloudflare's REST API and is **not**
        what boto3 wants; the S3 credentials are the two Key values.
      - These go straight into `backend/.env` and the Railway dashboard — **never into the repo,
        a commit, or a chat message.** `.env` is gitignored from Phase 1 onward.
- [ ] Configure the bucket's **CORS policy** — dashboard → **R2 object storage** → `fortu-cms` →
      **Settings** → *CORS Policy* → **Add CORS policy** → **JSON** tab (see Phase 5, step 7).
      Direct browser uploads fail without it, and the browser error says nothing useful about why
- [x] **Railway project created**, connected to the GitHub account
- [x] **GitHub repo** — `brebribre/signage-cms`
- [ ] In Railway: add the **Postgres** plugin, and create two services from the repo — `backend`
      and `frontend` (Phase 1b wires them up)
- [ ] Install locally: Python 3.11+, Node.js 20+, `uv`, Docker, Android Studio (for Phase 12)

---

## Phase 1: Backend Skeleton + Local DB Connection ✅ DONE

**Goal:** FastAPI runs, connects to Postgres, has one working endpoint.

Built beyond the plan: the **Alembic scaffolding** (`alembic.ini`, `migrations/env.py`,
`script.py.mako`) landed here rather than in Phase 2, because `run_migrations()` runs in the
lifespan from day one and needs something to run. There are no revisions yet, so `upgrade head` is
a working no-op; Phase 2 only adds the baseline.

Three deviations from what was written, all deliberate:

- **The dev server runs on port 8001, not 8000.** strava-comp's backend is already bound to
  8000 — this cost real debugging time here: `curl localhost:8000/health` returned a cheerful
  200 from *that* app while this one's database was stopped, so the failure path looked like it
  passed when it had never been exercised. Same reasoning as Postgres on 5434: both projects
  should run at once.
- **`/health` returns 503, not 500,** when Postgres is unreachable. Service Unavailable is what a
  dependency being down actually is, and Railway's health check treats any non-2xx as unhealthy
  either way.
- **`env.py` reads the database URL from `app.config`**, and `alembic.ini` leaves `sqlalchemy.url`
  empty. That file goes through configparser, where a password containing `%` fails on
  interpolation — a trap worth stepping around before a generated Railway password finds it.
- **`script.py.mako` imports `sqlmodel`.** SQLModel emits `sqlmodel.sql.sqltypes.AutoString` for
  `str` columns and the stock template doesn't import it, so the first autogenerated migration
  would fail with `NameError` at upgrade time. Cheaper to fix now than to debug in Phase 2.

Not copied from strava-comp: its `run_migrations()` stamps a pre-Alembic database before upgrading.
That solved a migration they had already lived through, and this database starts under Alembic.

1. Scaffold the backend with the layered structure — not flat modules:
   ```
   backend/
     app/
       main.py            app factory, CORS, router mount, lifespan
       config.py          pydantic-settings, loaded from .env
       api/               HTTP layer — the only layer that imports FastAPI
         router.py          aggregates every route module
         deps.py            get_db, later get_current_user / get_current_device
         routes/            one module per resource
       services/          business logic: takes a Session + plain args, returns plain data
       infra/             outbound: db.py, storage.py (S3/R2 client)
       models/            SQLModel tables, base.py holds utcnow() + tz_column()
       schemas/           Pydantic request/response shapes
     migrations/          Alembic
     scripts/             check_*.py checkpoint scripts
     requirements.txt
   ```
   **Dependency direction is `api → services → infra`.** Nothing in `services/` or `infra/`
   imports FastAPI; `infra/` never imports `services/`. `models/` and `schemas/` are leaves.
2. `requirements.txt`:
   ```
   fastapi>=0.115
   uvicorn[standard]>=0.32
   sqlmodel>=0.0.22
   psycopg[binary]>=3.2
   alembic>=1.14
   pydantic-settings>=2.6
   python-dotenv>=1.0
   itsdangerous>=2.2
   argon2-cffi>=23.1
   boto3>=1.35
   Pillow>=11.0
   httpx>=0.27
   ```
3. `docker-compose.yml` at the repo root — `postgres:16-alpine`, user/pass/db `signage`,
   published on **5434**, named volume, `pg_isready` healthcheck.
4. A root `.gitignore` covering `.env`, `.venv/`, `__pycache__/`, `node_modules/`, `dist/`,
   `frontend/.env*` (except `.example`), and `player/` build output. **Write this before the first
   commit, not after** — an R2 secret key in git history is a key rotation, not a `git rm`.
5. `backend/.env.example` with every name and no values:
   ```dotenv
   DATABASE_URL=postgresql+psycopg://signage:signage@localhost:5434/signage

   # Signs session cookies — python -c "import secrets;print(secrets.token_urlsafe(48))"
   SECRET_KEY=
   COOKIE_SECURE=false
   COOKIE_SAMESITE=lax

   # Cloudflare R2 (bucket fortu-cms)
   R2_ENDPOINT_URL=https://74c0ceb3565715dd70bbe3d4f585412f.r2.cloudflarestorage.com
   R2_BUCKET=fortu-cms
   R2_ACCESS_KEY_ID=
   R2_SECRET_ACCESS_KEY=
   MEDIA_MAX_BYTES=524288000
   PRESIGN_PUT_TTL_SECONDS=3600
   PRESIGN_GET_TTL_SECONDS=3600
   DEVICE_PRESIGN_TTL_SECONDS=21600

   FRONTEND_ORIGIN=http://localhost:5173
   EXTRA_CORS_ORIGINS=
   ```
   Copy it to `.env` and fill in the two R2 secrets locally.
6. In `config.py`, rewrite Railway's injected `postgresql://` to `postgresql+psycopg://` with a
   `field_validator` — psycopg2 isn't installed and SQLAlchemy assumes it otherwise.
7. `infra/db.py`: engine (`pool_pre_ping=True`), `session_scope()` generator, `run_migrations()`.
8. `models/base.py`: `utcnow()` and `tz_column()`. **Every datetime goes through `tz_column()`** —
   SQLModel otherwise maps `datetime` to `TIMESTAMP WITHOUT TIME ZONE` and silently drops offsets.
9. `GET /health` that runs `SELECT 1`. `/` redirects to `/docs`.
10. Run: `docker compose up -d`, then
   `cd backend && uv venv && uv pip install -r requirements.txt && .venv/bin/uvicorn app.main:app --reload`
11. Write `backend/README.md` documenting the layout, the dependency rule, and the Alembic workflow.

✅ **Checkpoint:** `/health` returns 200 with Postgres up and 500 with it stopped. `/docs` lists
the endpoint.

---

## Phase 1b: Deploy the Skeleton ✅ DONE

Live at **https://signage-cms-production.up.railway.app** — `/health` returns 200 against
Railway's Postgres, `/docs` renders.

What actually went wrong, in order, since none of it was the application:
1. **No start command.** Railpack detects Python and installs `requirements.txt` on its own, but
   refuses to guess how to start an `app/main.py` layout. Fixed with `backend/railpack.json`.
2. **`DATABASE_URL` unset**, so `config.py` fell back to `localhost:5434` and the container
   crash-looped at *"Waiting for application startup"* — migrations run in the lifespan, and there
   was no database to migrate. This is the failure the plan predicted, and it looks like a hang
   rather than an error, which is what makes it worth naming here.
   Fixed with the reference variable `${{Postgres.DATABASE_URL}}`.

Root Directory was already `backend`; the first build proved it by finding `requirements.txt`.

**Auto-deploy verified.** A plain `git push` started a deployment nobody asked for on the CLI,
which is the actual test — `railway redeploy --from-source` proves only that a source is connected,
not that a webhook exists, and that distinction is what cost time on strava-comp. The source here
was connected through the dashboard, and the trigger is real.

**Goal:** `git push` puts a working `/health` on the internet. Do this now, with one endpoint,
rather than at Phase 11 with fifteen.

Everything here is a deployment problem, not an application problem, and each one is far cheaper to
diagnose against a skeleton. The device API in Phase 10 needs a public HTTPS URL anyway.

1. **Connect the repo through the Railway dashboard** — Settings → Source → connect
   `brebribre/signage-cms`. ⚠️ **Setting the source any other way (e.g. `railway config apply`)
   registers no GitHub webhook, so pushes silently do not deploy.** This exact thing cost time on
   strava-comp; the symptom is a service that looks connected and never rebuilds.
2. **Root Directory per service** — `backend` for the API, `frontend` for the site. Without it
   Nixpacks builds the repository root, finds no `requirements.txt`, and fails or guesses wrong.
3. **Watch Paths** per service (`backend/**`, `frontend/**`) so a frontend commit doesn't redeploy
   the API and vice versa.
4. **Bind the port Railway gives you**, via `backend/railpack.json`:
   ```json
   { "$schema": "https://schema.railpack.com",
     "deploy": { "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT" } }
   ```
   Railpack detects Python and installs from `requirements.txt` on its own, but **it cannot guess
   a start command** and fails the build with *"No start command detected"*. Keeping it in the repo
   rather than in a dashboard field means the deploy is reproducible from a clone.
   Defaulting to 127.0.0.1 or to a fixed 8000 produces a service that builds, starts, logs nothing
   wrong, and fails every health check.
4b. Point Railway's **health check path** at `/health`, so a deploy that cannot reach Postgres is
   rolled back instead of going live and 503-ing.
5. **`DATABASE_URL`** as a reference variable — `${{Postgres.DATABASE_URL}}` — not a pasted string,
   so it survives the database being recreated. `config.py` already rewrites its `postgresql://`
   scheme to psycopg3 (Phase 1, step 6).
6. Set `SECRET_KEY` (a real one), `COOKIE_SECURE=true`, and the R2 variables in the Railway
   dashboard. **The R2 keys are entered there directly and never committed.**
7. Generate a public domain for each service, then set `FRONTEND_ORIGIN` on the backend to the
   frontend's URL and `VITE_API_BASE_URL` in `frontend/.env.production` to the backend's.
8. The frontend service builds with `vue-tsc -b && vite build` and serves with
   `serve -s dist -l $PORT` (`serve` as a dependency, `-s` so client-side routes don't 404 on
   reload).
9. Migrations run in the FastAPI lifespan, so the schema arrives with the deploy and there is no
   separate release step to forget.
10. Start `DEPLOY.md` now and add to it as you go — services, variables, and the gotchas above.

✅ **Checkpoint:** push to `main`, and the deployed `/health` returns 200 against Railway's Postgres
within a couple of minutes, without touching the dashboard.

---

## Phase 2: Database Schema ✅ DONE

**Goal:** every table the CMS needs, created by a single Alembic baseline.

Baseline `d00519ec4dca`. Seven tables; `check_schema_roundtrip.py` passes 16 checks and is
re-runnable, `alembic check` reports no drift, and `downgrade base && upgrade head` rebuilds the
database from empty.

Two things found by building it, both worth keeping:

- **SQLModel maps a Python enum to a native Postgres ENUM storing the member *name*.** The first
  baseline had `users.role` holding `'OWNER'` while the API speaks `'owner'` — two vocabularies for
  one concept, and `psql` showing the one nobody writes. Worse, adding a value later needs
  `ALTER TYPE ... ADD VALUE`, which **cannot run inside a transaction block**, and Alembic runs
  migrations in one. Replaced with `enum_column()` in `models/base.py`
  (`native_enum=False` + `values_callable`): VARCHAR, a CHECK constraint, lowercase values stored,
  enum members returned on read. The baseline was regenerated rather than patched — there was no
  data, and a follow-up migration that immediately alters what the previous one just created is
  worse than one correct file. `check_schema_roundtrip.py` now asserts the stored form, so this
  cannot regress silently.
- **`session.exec(delete(...))` executes immediately**, so a RESTRICT violation raises there, not
  at `commit()`. A `try` wrapped around the commit alone catches nothing and the check script
  crashes instead of passing.

Added beyond the plan's column list: `devices.poll_token` (unique, nullable). Phase 8 pairs a
device by polling with it rather than with the human-readable code, so a shoulder-surfed code
cannot be exchanged for a token. Putting it in the baseline costs nothing; adding it later costs a
migration.

Renamed from the plan: `Media.bytes` → **`size_bytes`**, because `bytes` shadows the builtin
inside the model class.

1. Define models in `app/models/`, one module per table:

   - **`Account`** — `id` (UUID pk), `name`, `created_at`. **The tenant.** Every resource below
     hangs off this, not off a user.
   - **`User`** — `id` (UUID), `account_id` FK **CASCADE**, `username` (**unique, lowercased on
     write**), `email` (nullable, unique when present), `password_hash`, `display_name`,
     `role` (`owner`|`manager`), `is_active`, `created_by` FK → users **SET NULL**, `created_at`
   - **`DeviceAccess`** — `user_id` FK **CASCADE**, `device_id` FK **CASCADE**, `granted_at`,
     composite primary key `(user_id, device_id)`. **Only consulted for `role='manager'`** — an
     owner reaches every device in their account without a row here, so granting is never something
     you can forget to do for yourself.
   - **`Media`** — `id` (UUID), `account_id` FK → accounts **CASCADE**, `created_by` FK → users
     **SET NULL**, `filename`, `kind`
     (`image`|`video`), `mime_type`, `bytes`, `width`, `height`, `duration_seconds` (null for
     images), `storage_key`, `thumbnail_key`, `checksum` (sha256 hex), `status`
     (`pending`|`ready`|`failed`), `created_at`
   - **`Playlist`** — `id` (UUID), `account_id` FK CASCADE, `created_by` FK → users SET NULL,
     `name`, `created_at`, `updated_at`
   - **`PlaylistItem`** — `id` (UUID), `playlist_id` FK **CASCADE**, `media_id` FK **RESTRICT**,
     `position` (int), `duration_seconds` (int — how long *this* slot shows; for a video, default
     to the media's own duration), unique `(playlist_id, position)`
   - **`Device`** — `id` (UUID), `account_id` FK CASCADE (**nullable until claimed** — an
     unclaimed device belongs to nobody yet), `name`,
     `location`, `pairing_code` (unique, nullable once claimed), `pairing_expires_at`,
     `token_hash` (sha256 of the device token — never the token itself), `playlist_id` FK
     **SET NULL**, `orientation` (`landscape`|`portrait`), `screen_width`, `screen_height`,
     `app_version`, `last_seen_at`, `paired_at`, `created_at`

2. **Why these FK behaviours**, since they are the decisions that bite later:
   - `PlaylistItem.media_id` is **RESTRICT**, not CASCADE: deleting a media file that is on air
     should be refused with a 409 naming the playlists, not silently punch a hole in a running
     screen.
   - `Device.playlist_id` is **SET NULL**: deleting a playlist must not delete the hardware. The
     screen falls back to its idle card.
   - `Media.account_id` is CASCADE: deleting the account removes the library. Deleting the
     *objects in R2* is a service-layer job, not a database one — note it in Phase 5.
   - `User.created_by` and `Media.created_by` are **SET NULL**: deleting a subuser must not delete
     the media they uploaded or the devices they claimed. Attribution is worth losing; the
     account's content is not. This is the single biggest reason for the `accounts` table.
   - `DeviceAccess` cascades from both sides: deleting a user or a device removes its grants, and
     a grant is never a reason a delete fails.

3. Set up Alembic (`alembic.ini` + `migrations/`), with `script_location` set to an absolute path
   in `_alembic_config()` so it works from any working directory. Generate the baseline **against
   an empty database** — autogenerating against one that already has the tables produces an empty
   migration that can't build a fresh environment.
4. Call `run_migrations()` in the FastAPI lifespan, so a deploy applies migrations.
5. `scripts/check_schema_roundtrip.py` — insert an account, an owner, a manager, media, a playlist
   with three items, a device and a grant; read them back; assert ordering, tz-aware timestamps,
   the RESTRICT refusal, the SET NULL on playlist delete, and that **deleting the manager leaves
   their uploaded media in place with `created_by` null**.

```bash
cd backend && .venv/bin/python -m scripts.check_schema_roundtrip
```

✅ **Checkpoint:** a fresh database built by `alembic upgrade head` round-trips every table, and
the two FK rules above are proven rather than assumed.

---

## Phase 3: Accounts, Users and Sessions ✅ DONE

**Goal:** an account exists, and every request knows *who* is calling and *what they may reach*.

`check_auth.py` passes 34 checks and is re-runnable. `alembic check` reports no drift — Phase 3 is
all behaviour, no schema.

Built beyond the plan:

- **Timing equalisation on login.** Returning early for an unknown identifier makes login
  measurably faster for identifiers that do not exist, which is an account-existence oracle no
  matter how identical the response body is. `passwords.waste_time_like_a_verify()` burns a
  verify's worth of CPU against a throwaway hash before raising.
- **`accessible_device_ids()` returns `None` for an owner**, not an exhaustive list. An owner's
  reach is defined by the account, so materialising it would invent state that can drift from the
  thing it describes. A manager gets the explicit list.
- **`normalise_username()` in the service, not only the schema.** SQLModel skips validation on
  `table=True` models and the unique index is case-sensitive, so without it `Alvin` and `alvin`
  are two users. The schema refuses bad input early; the service is the place nothing can bypass.
- **`email-validator`** added to `requirements.txt`, for `EmailStr`.

Two traps worth remembering, both found the hard way:

- **`TestClient` keeps a cookie jar across requests.** The client that performed signup is
  authenticated from then on, so `check_auth.py`'s "anonymous /me is 401" was quietly asserting the
  logged-in path and returning 200. Anything testing anonymous behaviour must clear the jar first.
- **FastAPI 0.141 no longer flattens included routers into `app.routes`** — they stay wrapped in an
  `_IncludedRouter`. Inspecting `app.routes` to confirm a route is registered gives a false
  negative; read `app.openapi()["paths"]` instead.

1. `services/passwords.py` — argon2 `PasswordHasher`: `hash_password`, `verify_password`. Verify
   **also reports whether the hash needs rehashing** (`ph.check_needs_rehash`), so parameter
   upgrades happen on next login instead of never.
2. `services/session.py` — `create_session_token(user_id)` / `read_session_token(token)` using
   `itsdangerous.URLSafeTimedSerializer` with `SECRET_KEY`, 30-day max age. The token carries the
   **user** id only; `account_id` and `role` are read from the database on every request, so
   revoking a subuser or narrowing their access takes effect immediately rather than whenever their
   cookie happens to expire.
3. Routes in `api/routes/auth.py`:
   - `POST /auth/signup` — `{ username, email, password, display_name }`. Creates the **`Account`
     and its `owner` user in one transaction**; 409 on a taken username or email.
   - `POST /auth/login` — `{ identifier, password }`. **One field, not two:** look the identifier
     up as a username, then as an email. Asking the user which kind of thing they are typing is a
     question the server can answer itself.
   - `POST /auth/logout` — clears the cookie.
   - `GET /me` — the current user **plus `account`, `role`, and (for a manager) the ids of the
     devices they may reach**, so the frontend can hide what it must not offer.
4. **401 with an identical body** for an unknown identifier, a wrong password, and a deactivated
   user. Three different messages turn the endpoint into an account-existence oracle, and
   `is_active` in particular would leak that a subuser was suspended.
5. Cookie flags from settings: `HttpOnly`, `SameSite` (`lax` local, **`none` + `Secure`** if the
   frontend ends up on a different domain than the API — otherwise browsers drop it silently),
   `Secure` in production.
6. `api/deps.py` grows three dependencies, and **these three are the whole authorization model**:
   ```python
   CurrentUser   # 401 if no valid cookie, or if the user is deactivated
   RequireOwner  # 403 unless role == 'owner' — user management only
   DeviceForUser # resolves a device_id: 404 outside the account, 404 for a
                 # manager with no grant, else the Device
   ```
   - **Every resource query filters by `account_id`**, in the service layer, not by remembering a
     `WHERE` in each route.
   - `DeviceForUser` returns **404, not 403**, for a device a manager wasn't granted. A manager
     should not be able to probe which devices exist outside their scope, and "you may not see
     this" and "this does not exist" should look identical from outside.
7. Media and playlists are **account-wide and shared** — a manager reads and creates freely.
   The one guardrail: a manager may delete only what they created (`created_by`), so one person
   cannot quietly remove a colleague's library. Owners may delete anything.
8. `scripts/check_auth.py` — signup creates account + owner; duplicate username and duplicate email
   both 409; login by username **and** by email; wrong password, unknown identifier and deactivated
   user return byte-identical 401s; `/me` reports role and grants; logout; a tampered cookie is
   rejected; a manager's cookie is refused by an owner-only route.

✅ **Checkpoint:** you can sign up, sign in with either credential, and `/me` reports the role.
Password hashes in the database start with `$argon2id$`.

---

## Phase 4: Frontend Skeleton ✅ DONE

**Goal:** the Vue app runs, has its layers in place, and can log in against Phase 3.

Verified by driving the real browser: signup → session cookie → `/media` shell → deep link to
`/devices` after a full reload with no login flash → sign out → login screen. `vue-tsc` clean,
production build 102 kB (39.8 kB gzip).

**The design system is taken from fortu.co.id by reading its computed styles**, not by eye:
Helvetica Neue, headings at weight 500 with `-0.025em` tracking at every size, pill buttons
carrying a 2px border in every variant, and no shadows anywhere. Tokens live in `src/style.css`;
`frontend/REQUIREMENTS.md` records them and the layer rules.

**The defining constraint is that there is no accent hue.** Nothing can mark "active" with colour,
so selection, focus and primary actions are expressed with ink fill and weight instead — a selected
nav row is ink on `raised`, a primary button is solid ink. One colour survives, `danger`, used only
for destructive actions and errors, and it is flagged in REQUIREMENTS.md §8 as removable.

Four things that cost time, all environmental rather than architectural:

- **npm's cache had root-owned entries**, which surfaced as `vite@undefined` and a bogus ERESOLVE
  peer conflict. A separate `--cache` dir did not fix it; the real problem was that the pinned
  versions were far behind this registry. Aligning to strava-comp's proven set (vite 8, vue-router
  5, pinia 4, typescript 6) installed cleanly. **`npm install | tail` hid the failure** — the pipe's
  exit code is what gets reported, so the harness called a failed install a success.
- **Reinstalling `node_modules` under a running dev server** leaves Vite serving a stale
  pre-bundle: `504 (Outdated Optimize Dep)` and a blank page. Restart Vite, don't debug the app.
- **`localhost:5173` and `127.0.0.1:5173` are different origins.** Opening the app on the wrong one
  fails with a bare CORS error naming neither. Both are now in `EXTRA_CORS_ORIGINS` for dev.
- **`baseUrl` is deprecated in TypeScript 6**; `paths` resolves relative to the tsconfig without it.

The frontend dev server is on 5173 and the backend on **8001** — see the Phase 1 note on why 8000
is unavailable locally.

1. Scaffold with Vite + Vue 3 + TypeScript. Add Tailwind v4 (`@tailwindcss/vite`), `vue-router`,
   `pinia`, `unplugin-icons` + `@iconify-json/material-symbols`. `@` aliases to `./src`.
2. Create the layer directories and **write `frontend/REQUIREMENTS.md` first**, stating the rule
   that governs them:

   ```
   View  →  Container  →  Hook  →  API hook  →  fetch
     ↘         ↘            ↘
      router    Reusable     Store (Pinia)
   ```

   | Layer | Lives in | Named | May contain |
   |---|---|---|---|
   | **View** | `src/views/` | `<Name>View.vue` | Layout + `<router-view>` outlets. Only these are routed to. |
   | **Container** | `src/containers/` | `<Name>Container.vue` | A feature. Calls hooks, routes, handles events. |
   | **Reusable** | `src/reusables/` | `<Name>.vue` | Generic pieces — buttons, tables, modals. Knows nothing about media or devices. |
   | **Hook** | `src/hooks/` | `use<Name>.ts` | State, transforms, business rules. |
   | **API hook** | `src/api/` | `use<Domain>Api.ts` | HTTP only — call, parse, type, return. |
   | **Store** | `src/stores/` | `use<Name>Store.ts` | Pinia. Cross-container shared state only. |

   **The rule stated plainly: TypeScript lives in containers or hooks, nowhere else.** No `fetch`
   in a container, no formatting in an API hook, no logic in a view.
3. `src/api/request.ts` — one shared helper: base URL from `VITE_API_BASE_URL`,
   **`credentials: 'include'` on every request** (the session is an HttpOnly cookie JS can never
   read), and non-2xx turned into a typed `ApiError` carrying `status` and FastAPI's `detail`.
4. `src/stores/useAuthStore.ts` + `src/hooks/useAuth.ts`. **Containers never import a store** —
   they go through the hook, which keeps the container rule to one thing.
5. Router with an auth guard that resolves the user **once** by calling `/me`, redirects to
   `/login` on 401, and lets routes opt out with `meta: { public: true }`. "Am I logged in?" is
   always answered by `/me`, never by inspecting storage.
6. Build the first reusables — `AppButton`, `AppInput`, `AppCard`, `AppModal`, `AppAlert`,
   `PageTitle`, `EmptyState` — and `LoginView` + `LoginContainer` + `SignupContainer`.
7. `SidebarView` — sidebar left, `<router-view>` right — as the shell every signed-in route uses.
8. `.claude/launch.json` with the frontend dev server on 5173.

✅ **Checkpoint:** sign up in the browser, land on the shell, reload and stay signed in, log out and
get bounced to `/login`. The backend's `FRONTEND_ORIGIN` must match or CORS blocks everything.

---

## Phase 5: Media Storage + Upload Pipeline (backend) ✅ DONE

**Goal:** a file gets from a browser into R2, with a database row that knows about it.

`check_media.py` passes 28 checks with storage stubbed (patching `app.infra.storage`, the one
module that touches boto3, so it runs with no credentials and no network). Separately, a **live
round trip against the real `fortu-cms` bucket** — presign PUT → upload → head → presign GET →
download → delete — confirms the credentials, endpoint, SigV4 signing and the checksum config all
work. That last part is what a stub can never prove.

Decisions made while building:

- **Allowed types are deliberately narrow**: JPEG, PNG, WebP, GIF and **h.264 MP4 only**. It is the
  one video combination a cheap Android stick is certain to decode in hardware, and refusing at
  upload with a message that says so is far kinder than a screen that stutters in a lobby. This
  closes open question 4 for the upload path; transcoding remains optional later.
- **A missing thumbnail does not fail the upload.** If the browser could not produce a poster
  frame, `thumbnail_key` is nulled and the tile falls back to a placeholder.
- **Completion is verified, not trusted.** `complete_upload` calls `head_object` and compares the
  stored size against the declared one; a client that claims "done" without uploading gets a 409
  instead of leaving a permanently broken row in the library.
- **Manager delete is restricted to their own uploads** (403 otherwise), the Phase 3 guardrail
  applied where it first bites. Owners may delete anything.
- **Delete order is row-then-object, deliberately.** If the R2 delete fails the row is already gone
  and the object is orphaned; an orphan costs storage, whereas rolling back a committed row costs
  correctness. A sweep script is Phase 14.

**Still yours to do in the Cloudflare dashboard** (step 7 above): the bucket CORS policy. Nothing
in Phase 5 needs it — the backend talks to R2 server-side — but **Phase 6 cannot upload a single
byte from the browser without it.**

1. `infra/storage.py` — one boto3 client, built once:
   ```python
   client = boto3.client(
       "s3",
       endpoint_url=settings.r2_endpoint_url,   # https://74c0…12f.r2.cloudflarestorage.com
       aws_access_key_id=settings.r2_access_key_id,
       aws_secret_access_key=settings.r2_secret_access_key,
       region_name="auto",                      # R2 has no regions; "auto" is required
       config=Config(
           signature_version="s3v4",
           # boto3 ≥1.36 sends CRC32 integrity headers by default, which several
           # S3-compatible providers reject. Verify against your boto3 version — if
           # uploads fail with an opaque 400, this is the first thing to try.
           request_checksum_calculation="when_required",
           response_checksum_validation="when_required",
       ),
   )
   ```
   Four functions and no more: `presign_put(key, content_type)`, `presign_get(key, ttl)`,
   `head_object(key)`, `delete_object(key)`. **Nothing else in the codebase constructs a URL or
   touches boto3** — that is what makes swapping storage a one-file change.
2. Storage keys are `media/{account_id}/{media_id}/{original_filename}` — account-prefixed so a bucket
   listing is comprehensible, and id-scoped so two files of the same name never collide.
3. The upload is **three calls**, because the file never passes through the API:
   - `POST /media/uploads` → `{ filename, content_type, bytes }`. Validates type and size against
     limits in settings, creates the `Media` row with `status='pending'`, returns
     `{ media_id, upload_url, thumbnail_upload_url }`.
   - The browser `PUT`s the file (and its generated poster JPEG) straight to those URLs.
   - `POST /media/{id}/complete` → `{ width, height, duration_seconds, checksum }`. Verifies the
     object actually exists and its size matches via `head_object`, then flips `status='ready'`.
     **A row that is never completed stays `pending` and is never listed** — that is what makes an
     abandoned upload harmless.
4. `GET /media`, `GET /media/{id}`, `DELETE /media/{id}`:
   - List returns only `status='ready'` rows owned by the caller, newest first, with a
     short-lived presigned thumbnail URL per row.
   - Delete **409s when the media is referenced by any playlist item**, with the playlist names in
     the detail — this is the RESTRICT from Phase 2 surfacing as a usable error rather than a 500.
   - Delete removes the R2 objects *after* the row commits. If the object delete fails, the row is
     already gone and the object is orphaned: log it and move on. Orphans cost storage; a failed
     delete that rolls back a committed row costs correctness.
5. Presigned GET URLs expire in **1 hour for the CMS** and **6 hours for a device manifest**
   (a screen needs long enough to download a large file over bad wifi). Minted per request; the
   bucket stays private, with no public URLs and no custom domain.
6. **Sign exactly the headers the browser will send.** Presigning with `ContentType` and then
   letting the browser send a different `Content-Type` fails with a signature mismatch that names
   nothing useful. The `PUT` sends `Content-Type` and nothing else — no ACL header, since **R2 has
   no ACLs** and `x-amz-acl` is rejected rather than ignored.
7. **Bucket CORS policy** — required before Phase 6 can upload anything from the browser:
   ```json
   [{
     "AllowedOrigins": ["http://localhost:5173", "http://127.0.0.1:5173"],
     "AllowedMethods": ["PUT", "GET", "HEAD"],
     "AllowedHeaders": ["Content-Type"],
     "ExposeHeaders": ["ETag"],
     "MaxAgeSeconds": 3600
   }]
   ```
   `PUT` is the load-bearing entry — the browser uploads straight to R2, so without it every
   upload fails. `Content-Type` must be allowed because it is the only header signed into the
   presigned URL. `ETag` must be *exposed* or the browser hides it even on a 200. Both
   `localhost` and `127.0.0.1` are listed for the reason given in the Phase 4 notes. Add the
   production frontend origin as a third entry once that is deployed.

   Cloudflare's placeholder policy (`http://localhost:3000`, `GET` only) is wrong on both
   counts: wrong port, and no `PUT`.

   **The Android player needs no entry here.** CORS is a browser mechanism; Media3 and OkHttp
   are native clients and are unaffected by this policy.
   Set it at **R2 object storage → `fortu-cms` → Settings → CORS Policy → Add CORS policy**,
   using the JSON tab. A missing origin here surfaces in the
   browser as a bare "network error" with no CORS message on the preflight, which is a genuinely
   miserable hour if you don't know to look.
8. **Lifecycle rule on the bucket**: abort incomplete multipart uploads after 1 day. Cheap
   insurance against paying for bytes no row points at.
9. `scripts/check_media.py` — a stubbed storage client asserts the three-step flow, the
   `pending`-not-listed rule, size/type rejection, cross-user 404 (not 403 — do not confirm the
   existence of another account's media), and the 409-on-referenced-delete.

✅ **Checkpoint:** a file uploaded with `curl` to a presigned URL becomes a `ready` media row, and
appears in `GET /media` with a working thumbnail URL.

---

## Phase 6: Media Library UI ✅ DONE

**Goal:** drag a video onto the page and see it in the library.

Verified end to end in the real browser against the real bucket: a 797 KB PNG dropped in, showed a
progress row, generated its own thumbnail, appeared in the grid at 1280×720, opened in detail with
a presigned preview, and deleted — **removing both objects from R2**, confirmed by listing the
bucket afterwards. Account scoping proved itself with live data: two accounts' libraries stayed
entirely separate.

**The checksum comes from R2's ETag, not from hashing in the browser.** This is a deviation worth
recording. `crypto.subtle.digest` has no streaming form — it needs the whole file in memory at
once, so a 500 MB video would freeze the tab and risk an allocation failure. The ETag is computed
server-side for free and is stable for the object's lifetime, which is all a cache key needs.
Checksums are therefore stored prefixed (`md5:…`), so the scheme is self-describing and Phase 10's
version hash is unaffected. It depends on `ExposeHeaders: ["ETag"]` in the bucket CORS policy;
without it the code falls back to `sha256:…` hashing, which works but is slow on large files.

Other decisions:

- **Probing happens in the browser** — dimensions from `naturalWidth`, duration from the video
  element, and a poster frame drawn to a canvas at **1 second, not 0**, because the first frame of
  a video is so often black that a 0-second poster is useless. All best-effort: a probe that fails
  yields nulls and the upload continues, since a video with no thumbnail is still a usable video.
- **`XMLHttpRequest`, not `fetch`, for the PUT** — fetch has no upload progress event, and a
  progress bar is the entire difference between a working upload and an apparently frozen tab.
- **Two uploads at a time.** A dozen parallel 200 MB PUTs saturate a venue's uplink and make every
  one of them slow, so the queue is the feature.
- **The storage error names the likely cause.** A failed PUT to R2 says to check the bucket CORS
  policy, because the browser reports that misconfiguration as a bare network error that mentions
  neither CORS nor the origin.

**Bug found and fixed after the first pass — a Vue reactivity trap worth knowing.** Uploads
completed correctly but the header stayed on "Uploading…" forever and finished rows never cleared.
The cause: `add()` pushed a **plain object** into `jobs` and then `runOne()` mutated *that same raw
reference*. Vue's deep reactivity wraps an object in a proxy when it is read out of the array, so
writing to the raw object goes straight past the proxy's setter and notifies nothing. The row still
showed "Done" — which is what made it confusing — only because `prepend()` mutates a different ref
and forced an incidental re-render; the `isUploading` **computed** was never invalidated, so it
stayed cached at `true` and also hid the Clear button. Fixed by creating each job with `reactive()`
so every mutation goes through the proxy. Successful rows now also dismiss themselves after 1.5s,
since the file is already visible in the grid by then; failures stay until read.

The general rule: **if a value is mutated from outside the component that owns the ref, make it
`reactive()` at creation.** Pushing raw objects into a `ref([])` and holding the raw reference is
silent — nothing errors, the data is even correct on next render, and only computeds give it away.

One process note: the backend had to be restarted before the media routes appeared. A long-running
`uvicorn` started **without `--reload`** keeps serving the app it was launched with, and the
frontend surfaced that as a flat `Not Found` on `GET /media` — which reads exactly like a routing
bug in code that is in fact correct.

1. `useMediaApi` (transport) + `useMediaUpload` (the business logic of an upload) +
   `useMedia` (the library list).
2. `useMediaUpload` owns the sequence: read the file, probe it in the browser
   (`<img>.naturalWidth`, `<video>.duration`, a `<canvas>` poster frame at ~1 s), hash it with
   `crypto.subtle.digest('SHA-256')`, call `/media/uploads`, `PUT` with `XMLHttpRequest` for a
   real **progress event** (`fetch` has no upload progress), then `/media/{id}/complete`.
3. Uploads run **two at a time**, queued — a dozen parallel 200 MB PUTs saturate a venue's uplink
   and make every one of them slow.
4. `MediaLibraryContainer` — grid of `MediaCard` reusables, filter chips for image/video, an
   `EmptyState`, and a `DropZone` reusable that takes files and emits them (it must not know what
   media is).
5. `MediaDetailContainer` at `/media/:id` — preview, metadata, "used in N playlists", delete.
6. The delete button surfaces the 409 as *"Used in Lobby Loop, Cafe Screen — remove it there
   first"*, not as a red toast saying "Conflict".

✅ **Checkpoint:** drag-and-drop an image and a video, watch both progress bars, see them in the
grid with correct dimensions and duration, and delete one.

---

## Phase 7: Playlists ✅ DONE

**Goal:** an ordered list of media with per-slot durations.

`check_playlists.py` passes 38 checks. Verified in the browser end to end: created a playlist, added
three files, dragged the third to the top, changed a duration, changed a fit, disabled an item,
saved, reloaded — and every one of those survived.

### Researched before implementing

Surveyed Xibo, OptiSigns, Yodeck, Play Digital Signage and EasySignage. What they all have:
per-item duration, drag-to-reorder, **per-item fit/scaling**, transitions, shuffle, item validity
dates, sub-playlists, dynamic (filtered) playlists, and non-media widgets.

**The finding that changed the design: per-item fit is universal, and we had no equivalent.**
Signage content is constantly mismatched to its screen — a 2000×2000 image on a 1920×1080 panel,
landscape video on a portrait screen. `Device.orientation` existed but nothing told the player *how
to fit* content, so it would have had to guess. Added as `PlaylistItem.fit`
(`contain` | `cover` | `stretch`, defaulting to `contain` because it neither crops nor distorts).
One enum column now versus a migration plus a player change later.

Also added, both cheap and both expected by every platform surveyed: `PlaylistItem.is_enabled`
(take a slot out of rotation without losing its position, duration and fit) and `Playlist.shuffle`.

**Deliberately deferred:**
- **Transitions** — cheap in schema, real work in the player. Media3 gives gapless playlist
  transitions free, but a crossfade needs two ExoPlayer instances swapping surfaces. Adding the
  field now would be an API that lies about what the hardware does. Revisit after Phase 12b shows
  what a gapless cut looks like on the real screens.
- **Item validity dates** — Xibo and OptiSigns put start/end dates on playlist *items*, not only on
  schedules, and it overlaps Phase 13's dayparting. They solve different problems ("this promo ends
  Friday" vs "breakfast menu until 11am"), so the decision belongs in Phase 13 where both can be
  designed together rather than becoming two competing time mechanisms.
- **Sub-playlists, dynamic playlists, widgets, background music** — each is real, none is needed to
  prove the loop works, and widgets in particular would reshape the media model.

### Device preview (added beyond the plan)

The playlist editor previews each item on a **real screen shape**, at real durations, with the
item's own fit applied — because the questions "how much black will this have" and "what will Fill
cut off" cannot be answered from a thumbnail grid, and answering them on the wall is too late.

- **Presets cover portrait and landscape**, portrait first. Tall 4K totems are one of the
  commonest signage formats and a landscape-only preview would quietly mislead about every one of
  them. Custom sizes are supported, and the choice is remembered per browser.
- **The fit mapping is exact, which is what makes the preview trustworthy**: CSS `object-fit`
  `contain`/`cover`/`fill` correspond one-to-one with Media3's `RESIZE_MODE_FIT`/`ZOOM`/`FILL`.
  This is a model of the player, not an impression of it.
- **Two warnings that turn invisible problems into visible ones**: how much of an image `cover`
  crops away (a 1600×900 image on a 4K portrait totem loses 68%), and whether the media is lower
  resolution than the panel and will therefore look soft.
- **Play loop** steps through enabled items at their real durations, driven off the *draft* rather
  than the saved playlist — the point is seeing an unsaved change before committing it to a wall.
- `MediaRead` and playlist items now carry a presigned `url`. Presigning is a local HMAC, so N
  items cost N cheap computations and no network calls; previewing the 480px thumbnail instead
  would misreport both sharpness and cropping, and would fire the upscaling warning falsely.

Phase 9 will add registered devices to the preset list — `Device.screen_width`/`screen_height` are
already reported on every heartbeat, so "preview as Lobby screen" becomes a lookup rather than a
new mechanism.

**Two bugs found by building it, both caught before shipping:**

- **The list and the detail disagreed.** The detail excluded disabled items from its count and
  total; the list's SQL aggregate did not, so one playlist read "3 items · 0:45" in the list and
  "2 items · 0:35" in the editor. Fixed by filtering `is_enabled` in the **JOIN condition** rather
  than a `WHERE` — with an outer join a `WHERE` would drop playlists whose every item is disabled
  instead of showing them with zero. Now guarded by a check that asserts the two agree.
- **The preview lied about landscape.** `width: 100%` plus a `max-height` cap makes a wide
  container clamp the height while the width stays full, so a 16:9 panel rendered at 2.21:1 —
  precisely the thing a preview must never do. Fixed by deriving the width from the height cap;
  all four presets now measure within 0.02 of their true ratio.

### Notes from the build

- **The migration needed hand-editing, exactly as `backend/README.md` warns.** Autogenerate wrote
  three `NOT NULL` columns with no `server_default`, which works only on an empty table — Postgres
  refuses to add a NOT NULL column to existing rows with nothing to put in them. Rewritten as the
  standard two-step: add *with* a default so existing rows backfill, then drop the default so the
  schema matches the model and `alembic check` stays clean (env.py sets
  `compare_server_default=True`, so a lingering default reads as drift).
- **Counts and totals ignore disabled items.** The number people read as "how long is this loop"
  has to match what a screen actually plays, or it is worse than no number.
- **Editing is explicitly saved, never autosaved.** Rearranging a live playlist must not push
  half-finished states onto a wall of screens, so Save is the commit point and the button is
  disabled until something actually changed.
- **A draft row is keyed by a fresh UUID, not by media id** — the same file may legitimately appear
  twice in one loop, and keying by media would make Vue treat the two as one row.

1. Backend, `api/routes/playlists.py`:
   - `GET /playlists` — with item count and total duration
   - `POST /playlists` — `{ name }`
   - `GET /playlists/{id}` — items in order, each with its media joined in
   - `PATCH /playlists/{id}` — rename
   - `PUT /playlists/{id}/items` — **replaces the whole list**: `[{ media_id, duration_seconds }]`
     in order. One endpoint, one transaction, no reorder/insert/move verbs. This is the single
     highest-leverage simplification in the project: drag-and-drop reordering produces a new array
     anyway, and per-item mutation would need conflict handling for a problem nobody has.
   - `DELETE /playlists/{id}` — 409 if assigned to any device, naming them
2. Validation in `services/playlists.py`: every `media_id` must be `ready` and owned by the caller;
   `duration_seconds` between 1 and 3600; an empty list is legal (a playlist being emptied is not
   an error). Positions are assigned from the array index — the client never sends them.
3. A video item's default duration is its own `duration_seconds`; the UI lets it be overridden
   (cutting a long video short is a real thing signage does), an image defaults to 10 s.
4. Frontend: `usePlaylistApi`, `usePlaylists`, `usePlaylistEditor`, and
   `PlaylistEditorContainer` — a reorderable list (HTML5 drag events; no library), an
   "Add media" `AppModal` reading the Phase 6 library, a per-row `DurationInput`, and a running
   total duration in the header.
5. The editor is **explicitly saved**, not autosaved. Rearranging a live playlist should not push
   half-finished states onto a wall of screens; the Save button is the commit point.
6. `scripts/check_playlists.py` — create, replace items twice and assert no duplicate rows and
   correct ordering, reject another user's media, reject an unready media, empty the list,
   and 409 the delete of an assigned playlist.

✅ **Checkpoint:** build a three-item playlist in the browser, reorder it, save, reload, and get the
same order back.

---

## Phase 8: Devices — Pairing and Registration (backend)

**Goal:** a screen with no keyboard becomes a row in your account.

The pairing flow, and why it is shaped this way: a signage device has no browser to log into and
no way to type a password. So **the device asks for a code, and the human types the code into the
CMS** — the credential is minted by the server and handed to the device, never entered on it.

1. `POST /devices/pair` — **unauthenticated**, called by the device on first boot.
   Creates an unclaimed `Device` row and returns `{ pairing_code, poll_token, expires_at }`.
   The code is **6 characters from an unambiguous alphabet** (no `0/O`, `1/I/L`) — it gets read off
   a TV across a room. It expires in 15 minutes; an unclaimed row is deleted on expiry.
2. `GET /devices/pair/{poll_token}` — the device polls every 5 s. `202` while unclaimed;
   once claimed, `200 { device_id, device_token }` **once**, then the poll token is destroyed.
3. `POST /devices/claim` — **authenticated**, called by the CMS: `{ pairing_code, name, location }`.
   Looks up the unexpired unclaimed code (404 otherwise), sets `account_id` and `created_by`,
   generates a
   `secrets.token_urlsafe(32)` device token, stores **only its sha256** in `token_hash`, and holds
   the plaintext for exactly one pair-poll to collect.
4. Rate-limit `/devices/claim` per user — 6 characters is a small space and guessing a pending code
   would attach someone else's screen to your account. 10 attempts/minute is plenty for typing.
5. `GET /devices`, `PATCH /devices/{id}` (name, location, orientation, **`playlist_id`**),
   `DELETE /devices/{id}`, `POST /devices/{id}/unpair` (clears `token_hash` so the screen returns
   to showing a fresh pairing code — the fix for a stolen or re-sited device).
6. `deps.get_current_device` — reads `Authorization: Bearer <token>`, hashes it, looks up
   `token_hash`. **Device auth and user auth are separate dependencies and never overlap**: a
   device token can never call `/media`, and a session cookie can never call `/device/manifest`.
7. `scripts/check_devices.py` — full round trip: pair → poll returns 202 → claim → poll returns the
   token once → second poll 404 → device token authenticates → wrong token 401 → expired code
   rejected → another user's device is 404 → unpair invalidates the token.

✅ **Checkpoint:** the pairing handshake completes end to end with two `curl` sessions standing in
for a device and a browser.

---

## Phase 9: Device UI

**Goal:** register and manage screens from the website.

1. `useDeviceApi`, `useDevices`, `DeviceListContainer` — one row per screen with a `StatusDot`
   (green < 2 min since `last_seen_at`, amber < 15 min, grey beyond), the assigned playlist, and
   the location.
2. `DevicePairContainer` in an `AppModal` — a big code input, a name and a location field. The
   copy tells the user where to read the code: *"Type the code shown on the screen."*
3. `DeviceDetailContainer` at `/devices/:id` — assign a playlist from a dropdown, rename,
   set orientation, see last seen / app version / reported resolution, unpair, delete.
4. Assigning a playlist is a `PATCH` and takes effect on the device's next poll. The UI says
   **"Updating — takes up to 30 seconds"** rather than pretending it is instant, because a screen
   that hasn't changed yet should not look broken.

✅ **Checkpoint:** pair a device (still faked with curl), name it, assign a playlist, and see it in
the list with a status dot.

---

## Phase 9b: Subusers and Device Access ✅ DONE

**Goal:** the owner delegates a subset of the screens without handing over the account.

`check_users.py` passes 41 checks. Verified in the browser: created manager `cafe-staff` granted
one of three screens, then signed in as them — `GET /devices` returned exactly `["Cafe panel"]`,
`GET /users` returned **403**, and media (3) and playlists (1) stayed fully visible, which is the
shared-library rule working rather than a leak.

**Built out of order.** The plan puts this after Phases 8 and 9 because grants need devices to
exist. It was built first anyway, so `GET /devices` landed here — the minimum needed to assign a
grant against something real. Phase 8 adds pairing, claiming and unpairing around it; the listing
already scopes correctly (owners see the account, managers see their grants, unclaimed devices
belong to nobody and appear for no one).

Decisions worth recording:

- **The owner is the password recovery path.** `POST /users/{id}/password` sets a subuser's
  password directly and there is no email reset flow — which is the entire reason email is
  optional on a user. A screen manager created by the owner often has no address to send one to.
- **Grants are replaced wholesale**, same shape as `PUT /playlists/{id}/items` and for the same
  reason: the UI is a checkbox list that produces a complete set anyway. Duplicate ids collapse.
- **Cross-account references are 404, never 400.** Granting a device that exists in another
  account returns "Device not found", because calling it *invalid* would confirm it exists.
- **Deactivation bites on the next request, not the next login** — `is_active` is read per request
  (Phase 3), so a suspended manager's existing cookie stops working immediately. Asserted.

**A guard that turned out to be unreachable, kept deliberately.** `LastOwner` refuses removing an
account's final active owner. Over HTTP it can never fire: to act you must be an active owner, and
the self-guard blocks acting on yourself, so at least one active owner always remains besides the
target. My first check appeared to exercise it but was actually passing on a 401 from a
deactivated cookie — a green tick proving nothing. It is now asserted at the **service layer**
against a fabricated state that HTTP cannot reach, and the guard stays as defence-in-depth for
whenever role promotion or invitations arrive.

A second check in the same script was worse: it ended in `or True` and could not fail. Both are
fixed. Worth remembering that a passing check script is only as good as its weakest assertion.

Built here, after Phase 9, because granting access to devices requires devices to exist.

1. Backend, `api/routes/users.py`, all behind `RequireOwner`:
   - `GET /users` — everyone in the account, with their role, active flag and device count
   - `POST /users` — `{ username, password, display_name, email?, device_ids[] }`; creates the
     manager and its grants in one transaction; 409 on a taken username
   - `PATCH /users/{id}` — rename, set `is_active`
   - `POST /users/{id}/password` — the owner sets a new password directly. **There is no email
     reset flow**, and that is the point of decision #5: a subuser may have no email address, so
     the owner is the recovery path.
   - `PUT /users/{id}/devices` — **replaces the whole grant set**: `{ device_ids: [...] }`. Same
     whole-array-replace shape as `PUT /playlists/{id}/items`, for the same reason — the UI is a
     checkbox list that produces a complete set anyway.
   - `DELETE /users/{id}` — removes the manager and their grants; their media and devices survive
     with `created_by` nulled
2. Guardrails in `services/users.py`, each of which is a real way to lock yourself out:
   - an owner cannot delete or deactivate **themselves**
   - the account must always keep **at least one active owner**
   - a manager cannot be created with a device from another account (404, not 400 — same
     reasoning as `DeviceForUser`)
   - deactivating a user takes effect on their **next request**, not their next login, because
     `role` and `is_active` are read per request (Phase 3, step 2)
3. Frontend at `/settings/users`: `UserListContainer`, and a `UserFormContainer` in an `AppModal`
   with username, display name, password, and a **checkbox list of the account's devices**.
4. The sidebar hides Users entirely for a manager, and the device list shows only granted devices.
   **Hiding is a UI courtesy, not the control** — the server is what enforces it, and the check
   script proves that by calling the endpoints directly with a manager's cookie.
5. `scripts/check_users.py` — create a manager with two of three devices; the manager sees exactly
   two in `GET /devices`; the third is a **404** by id; the manager can assign a playlist to a
   granted device and cannot to the third; `PUT /users/{id}/devices` replaces rather than appends;
   a manager calling any `/users` route gets 403; the last-owner and self-deletion guards both
   refuse; a deactivated manager's existing cookie stops working on the next call.

✅ **Checkpoint:** a subuser signs in with a username, sees two screens out of three, and cannot
reach the third by any route including guessing its id.

---

## Phase 10: Device Sync API

**Goal:** the contract the screen actually runs on. Get this right and the player is easy.

1. `GET /device/manifest` (device token) returns everything needed to play, and nothing else:
   ```jsonc
   {
     "version": "sha256:1f3a…",         // changes iff the content changes
     "device": { "name": "Lobby", "orientation": "landscape" },
     "playlist": { "id": "…", "name": "Lobby Loop" },
     "items": [
       { "id": "…", "kind": "video", "url": "https://…signed…",
         "checksum": "sha256:…", "bytes": 48210233, "duration_seconds": 30 }
     ]
   }
   ```
2. **`version` is derived, never stored as a mutable flag.** It is a hash of
   `(playlist_id, [(item id, media checksum, duration, position)])`. Nothing has to remember to
   bump it, so no code path can forget to — the class of bug where a screen silently keeps playing
   last week's content simply cannot occur.
3. The endpoint honours `If-None-Match` and returns **304** when the version matches. A screen
   polling every 30 s therefore costs a few hundred bytes an hour when nothing has changed.
4. **Presigned URLs expire in 6 hours, but the checksum is stable.** The device caches files by
   checksum, so a re-issued URL for an unchanged file is not a re-download. This split — volatile
   URL, stable identity — is what makes the cache work.
5. A device with no playlist gets `"playlist": null` and an empty `items` array. That is a valid
   state, not a 404: a newly paired screen is in it.
6. `POST /device/heartbeat` — `{ app_version, screen: {width, height}, current_item_id, errors[] }`.
   Updates `last_seen_at`, `app_version`, reported resolution. Returns `{ version }` so a device
   that heartbeats more often than it polls learns early that it should re-fetch.
7. Errors reported by the device are logged, not stored, until Phase 14 gives them a table.
8. `scripts/check_device_sync.py` — manifest for an assigned playlist; `304` on a repeat with the
   ETag; the version **changing** after a reorder, a duration edit, and a playlist reassignment,
   and **not changing** after renaming the device; empty manifest for an unassigned device; 401
   without a device token; heartbeat updating `last_seen_at`.

✅ **Checkpoint:** the version hash provably tracks content and only content.

---

## Phase 11: Production Hardening

The pipeline has been live since Phase 1b. What's left is everything that only breaks once there
are real sessions, real uploads, and a real screen polling from outside your network.

1. **The cross-domain cookie**, which is the single most common way this deployment fails: if the
   frontend and API are on different domains, the backend needs `COOKIE_SAMESITE=none` **and**
   `COOKIE_SECURE=true`, and the frontend origin must appear in `FRONTEND_ORIGIN` /
   `EXTRA_CORS_ORIGINS`. Get one of the two wrong and the browser drops the session cookie
   **silently** — no console error, just a permanent 401 loop that looks like broken auth.
   Putting both services behind one domain avoids the whole class of problem, and is worth doing
   if a custom domain is on the cards anyway.
2. **R2 CORS for the production origin** — add it alongside `http://localhost:5173` (Phase 5,
   step 7). Uploads work locally and fail in production otherwise.
3. Custom domain, if there is one. Do it **before** any device is paired: the device stores the API
   base URL it was built with, and moving it afterwards means re-provisioning hardware.
4. Confirm `COOKIE_SECURE=true`, a rotated `SECRET_KEY`, and `LOG_LEVEL=INFO` in production.
5. Verify Railway's Postgres **backup schedule** is on, and enable **object versioning** on the R2
   bucket. A media library is the one thing here that cannot be rebuilt from code.
6. Finish `DEPLOY.md`: every variable, the two CORS surfaces (API and R2), and the runbook for
   rotating an R2 key.

✅ **Checkpoint:** sign in on the deployed site in a fresh browser profile, upload a file, and pair a
device from a phone on mobile data — outside your network, which is the only test that proves it.

---

## Phase 12a: Android App — Pairing

**Goal:** a screen with no keyboard puts itself into your account.

**Stack**, all of it deliberate:

| Concern | Choice | Why |
|---|---|---|
| Language / UI | **Kotlin + Jetpack Compose** | The pairing screen, idle card and debug overlay are the only UI; Compose is far less ceremony than XML for that |
| Video | **Media3 (ExoPlayer)** | Hardware decoder selection, offline cache, and a playlist that mixes images and video |
| HTTP | **OkHttp + kotlinx.serialization** | Two endpoints. Retrofit is overkill for `GET /device/manifest` and `POST /device/heartbeat` |
| Token storage | **DataStore** | See note 4 below on why encryption isn't the control that matters here |
| Sync loop | **A coroutine in a foreground service** | **WorkManager cannot do this** — its minimum periodic interval is 15 minutes, and the poll is 30 seconds |

1. Single `Activity`, `Compose`, landscape-locked, `FLAG_KEEP_SCREEN_ON`, immersive full-screen
   (`WindowInsetsControllerCompat` hiding both bars). No action bar, no chrome.
2. Boot: read the device token from DataStore. If absent → `POST /devices/pair`, then show the
   pairing code **full-screen in very large type**, with the account name to type it into. Poll
   `GET /devices/pair/{poll_token}` every 5 s until it returns the token, store it, continue.
3. The pairing screen is the app's error state too: an unpaired, revoked, or 401'd device always
   lands back here rather than on a black screen. **A screen showing a pairing code is diagnosable
   from across the room; a black one is not.**
4. The device token is a bearer credential sitting on hardware you physically control. DataStore
   plain is the right level: `androidx.security-crypto` is deprecated, a rooted attacker with the
   device in hand wins regardless, and the actual controls are Device Owner mode (Phase 12c) plus
   `POST /devices/{id}/unpair` on the server. Encrypting it locally would be security theatre.
5. A **debug overlay** on a long-press or a key combo: device id, manifest version, cached bytes,
   free space, last poll, last error. This is the only way to diagnose a screen you are standing in
   front of, and it costs almost nothing to build now.

✅ **Checkpoint:** a factory-fresh device shows a code, you type it into the CMS, and it moves to the
idle card within seconds. Killing and relaunching the app does not re-pair.

---

## Phase 12b: Android App — Sync and Playback

**Goal:** the loop plays, offline, and picks up changes.

1. **Sync loop** in a foreground service: fetch `GET /device/manifest` with the stored `ETag` →
   `304` means sleep 30 s and go again → a new version means reconcile the download set.
2. **Downloads through Media3's `DownloadManager`.** This is the piece that makes native worth it:
   it handles queueing, resumption after a network drop, progress, and a
   `CacheDataSource`-backed store that ExoPlayer plays directly from. Point it at the presigned URL
   with the **checksum as the download id**, so a re-issued URL for unchanged content is
   recognised as already-downloaded rather than re-fetched.
3. Remove downloads whose checksum is no longer in the manifest, **after** the new set is fully
   downloaded — never before. A screen must not be left with a half-populated cache if the network
   dies mid-swap.
4. **Play from the cache, always** — never stream from the presigned URL. A venue's wifi dropping
   should have no visible effect whatsoever; that is the entire point of caching by checksum.
5. **The loop is one ExoPlayer playlist,** built from `MediaItem`s in manifest order, with
   `repeatMode = REPEAT_MODE_ALL`. Media3 supports images as playlist items via
   `setImageDurationMs`, so a mixed image/video loop needs no scheduler of our own and transitions
   are gapless. ⚠️ **Verify this against the Media3 version you pin** — image support arrived
   relatively recently. If it isn't there, fall back to a Compose `Image` layered over the player
   surface and a coroutine timer, which is where the hand-rolled scheduler would have been anyway.
6. Crossfades are **not** free the way gapless is — they need two `ExoPlayer` instances swapping
   surfaces. Decide whether it's worth it after seeing a gapless cut on the real hardware; a clean
   cut looks fine, and a black frame between items is the only genuinely unacceptable outcome.
7. On a version change, **finish the current item first**, then swap the playlist. Cutting mid-item
   to apply an update is the difference between a CMS and a glitch.
8. `POST /device/heartbeat` every 60 s with `app_version`, screen size, current item, and any
   playback errors. On total network failure keep playing the last good cached manifest
   indefinitely — **a screen must never go black because a server is down.**
9. Idle card (device name + "No content assigned") when the playlist is empty. This is a valid
   state for a freshly paired screen, not an error.
10. Watchdog: if ExoPlayer reports an unrecoverable error, or nothing has advanced for 5 minutes,
    restart the player. Uptime is measured in months, and something will eventually wedge.

✅ **Checkpoint:** the device plays a loop, keeps playing with the network unplugged for an hour,
picks up a playlist change within 30 s of Save, and survives a power cut.

---

## Phase 12c: Kiosk, Provisioning and Updates

**Goal:** hardware you can ship and not visit again.

1. **Kiosk**, in ascending strength — pick per deployment:
   - `startLockTask()` (screen pinning) — works on any device, dismissible with a button combo
   - a `CATEGORY_HOME` intent filter, so the app *is* the launcher
   - ✅ **Device Owner** via `adb shell dpm set-device-owner` on a **factory-reset** device — real
     lock task mode with no exit, and the right answer for hardware you own. It must be set before
     any account is added to the device, which is why it is a provisioning step and not a setting.
2. `BOOT_COMPLETED` receiver + foreground service, so a power cut is invisible and Android doesn't
   reclaim the process.
3. **Silent self-update**: Device Owner grants `PackageInstaller` without a user prompt. Add
   `latest_apk_version` / `apk_url` to the heartbeat response, and let the device install and
   restart itself overnight. This is the single feature that decides whether a fleet is
   maintainable, and it is nearly free once Device Owner is in place.
4. Disable everything that interrupts a screen: system update prompts, screensaver, lock screen,
   and Play auto-updates for other apps — all settable through the Device Owner policy.
5. `player/README.md` records the provisioning runbook: factory reset → skip account setup →
   `adb install` → `dpm set-device-owner` → launch → pair. Write it while you are doing it the
   first time, not from memory afterwards.
6. Target the oldest Android you actually own. Signage sticks and panels run several versions
   behind, and that constraint should be discovered at Phase 12a, not here.

✅ **Checkpoint:** a factory-reset device is provisioned from the runbook in under ten minutes, cannot
be exited, comes back from a power cut into the loop, and takes an app update without a visit.

---

## Phase 13: Scheduling (dayparting)

Once the loop is reliable, decide *when* each playlist runs.

- `schedules` table: `device_id`, `playlist_id`, `days_of_week` (bitmask), `starts_at`/`ends_at`
  (local time-of-day), `priority`.
- Resolution happens **server-side, inside the manifest**: the device asks "what do I play?" and is
  told. Putting the calendar on the device means every screen needs the right clock, the right
  timezone, and the same rules — three ways to disagree with the CMS.
- The device's timezone comes from the device row, set in the CMS. The manifest gains a
  `valid_until`, so a screen knows to re-poll at the boundary rather than at the next 30 s tick.
- The version hash gains the resolved schedule window, so a daypart change is a content change and
  the existing sync machinery carries it with no new code.

---

## Phase 14: Operations

Worth building only once screens are in the wild.

- **Device health page** — last seen, uptime, the reported errors from `POST /device/heartbeat`,
  given a `device_events` table.
- **Storage quota** per account, enforced at `POST /media/uploads` where it can still be refused
  cleanly.
- **Orphan sweep** — a script listing R2 objects with no media row (the Phase 5 failed-delete case).
- **Proof-of-play log** — what actually played, when, per device. The one report a signage
  customer always eventually asks for; cheap if the heartbeat already reports `current_item_id`.
- **Backups** — Railway Postgres snapshot schedule, and R2 versioning on the bucket.

---

## Endpoint summary

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /auth/signup` · `POST /auth/login` · `POST /auth/logout` · `GET /me` | cookie | Accounts; login takes username **or** email |
| `GET/POST /users` · `PATCH/DELETE /users/{id}` · `POST /users/{id}/password` | **owner** | Subusers |
| `PUT /users/{id}/devices` | **owner** | Whole grant-set replace |
| `POST /media/uploads` → `PUT` to R2 → `POST /media/{id}/complete` | cookie | Three-step upload |
| `GET /media` · `GET /media/{id}` · `DELETE /media/{id}` | cookie | Library |
| `GET/POST /playlists` · `GET/PATCH/DELETE /playlists/{id}` | cookie | Playlists |
| `PUT /playlists/{id}/items` | cookie | Whole-list replace |
| `POST /devices/pair` · `GET /devices/pair/{poll_token}` | **none** | Device-side pairing |
| `POST /devices/claim` | cookie | Human types the code |
| `GET /devices` · `PATCH/DELETE /devices/{id}` · `POST /devices/{id}/unpair` | cookie | Screen management — **scoped to granted devices for a manager** |
| `GET /device/manifest` · `POST /device/heartbeat` | **device token** | Runtime |

## Planned screens

| Route | View | Containers |
|---|---|---|
| `/login`, `/signup` (public) | `LoginView` | `LoginContainer` / `SignupContainer` |
| `/media` | `SidebarView` | `SidebarContainer` + `MediaLibraryContainer` |
| `/media/:id` | `SidebarView` | `SidebarContainer` + `MediaDetailContainer` |
| `/playlists` | `SidebarView` | `SidebarContainer` + `PlaylistListContainer` |
| `/playlists/:id` | `SidebarView` | `SidebarContainer` + `PlaylistEditorContainer` |
| `/devices` | `SidebarView` | `SidebarContainer` + `DeviceListContainer` (+ `DevicePairContainer` in a modal) |
| `/devices/:id` | `SidebarView` | `SidebarContainer` + `DeviceDetailContainer` |
| `/settings/users` (owner only) | `SidebarView` | `SidebarContainer` + `UserListContainer` (+ `UserFormContainer` in a modal) |

`/` redirects to `/media` — the library is what you open the CMS to work in. **The player is not a
route here** — it is the separate `player/` package (Phase 12a).

---

## Open questions

1. **How many screens, and how many subusers?** This is the one number that decides whether
   decision #7 holds. Up to ~50 screens, per-device grants and a checkbox list are the better
   design. Past that, **device groups** become the primitive — assign a playlist to a group, grant
   a subuser a group — and they would slot in between Phases 9 and 9b, with the grant table keyed
   by group instead of device. Everything else in the plan is unaffected either way.
2. **Which Android hardware and version?** This decides Phase 12b and 12c. Device Owner mode needs
   a factory reset and gives a screen that genuinely cannot be exited; screen pinning works on
   anything but is weaker. The Android version sets the minSdk and, with it, which Media3 features
   are available. **Get one device in hand before Phase 12a** — the answer to "does it decode this
   in hardware" is not knowable from a spec sheet.
3. **Does anything need to be live?** An emergency message that must appear in seconds, rather than
   in thirty, is the one requirement that would justify revisiting decision #4 and adding a
   websocket or web push channel.
4. **Video transcoding.** Right now whatever is uploaded is what plays. **h.264/AAC in MP4 is the
   only combination a cheap Android stick is certain to decode in hardware** — h.265 and VP9 are a
   coin flip, and software decoding a 4K file means dropped frames rather than a clean failure.
   Either constrain uploads to h.264 with a clear error message, or normalise on upload with ffmpeg
   in a worker service (never in the API process). Media3's `MediaCodecInfo` can report what the
   device actually supports, so the player can tell you which files a given screen can't play
   instead of stuttering through them.
5. **Design direction.** strava-comp is dark-only with a pine accent, and its tokens live in
   `style.css`. Reuse it, or pick a palette for this project before Phase 4 builds the reusables?
