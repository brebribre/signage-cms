# Backend — Signage CMS

FastAPI + SQLModel + Postgres.

## Layout

```
app/
  main.py        composition root: creates the FastAPI app, CORS, lifespan, mounts the router
  config.py      settings loaded from .env (absolute path, so any cwd works)

  api/           HTTP layer — the only layer that knows about FastAPI
    router.py      aggregates every route module
    deps.py        shared dependencies (get_db; later CurrentUser, RequireOwner, DeviceForUser)
    routes/        one module per resource: health.py, later auth.py, media.py, devices.py …

  services/      business logic — takes a Session + plain args, returns plain data
                 raises domain errors; routes translate them to HTTP

  infra/         outbound connections
    db.py          engine, session, migration runner
    logging.py     one place that configures logging
                   later: storage.py (the only module that touches boto3)

  models/        SQLModel tables; base.py holds utcnow() and tz_column()
  schemas/       Pydantic request/response shapes exposed by the API
```

**Dependency direction: `api → services → infra`.** Nothing in `services/` or `infra/`
imports FastAPI, and `infra/` never imports `services/`. `models/` and `schemas/` are
leaf modules both upper layers may read.

Adding an endpoint:
1. shape in `schemas/`, 2. logic in `services/`, 3. thin route in `api/routes/`,
4. register it in `api/router.py`.

## Running locally

Postgres, from the repo root — **host port 5434**, so this can run alongside other projects:

```bash
docker compose up -d
```

Install:

```bash
cd backend && uv venv && uv pip install -r requirements.txt
```

Configure — copy the example and fill in the two R2 keys:

```bash
cp backend/.env.example backend/.env
```

Run:

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs — `/` redirects there. `/health` returns 200 only if a
`SELECT 1` against Postgres succeeds, and **503** when it doesn't.

## Database migrations

Alembic owns the schema. `run_migrations()` runs in the FastAPI lifespan, so a deploy
applies its own migrations and there is no separate release step to forget.

Add a column or table:

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "add device access"
```

**Read the generated file before committing it.** Autogenerate is a starting point, not an
oracle: it misses renames (it sees a drop plus an add, losing the data) and cannot write
backfills.

```bash
cd backend && .venv/bin/alembic upgrade head
```

Useful:
- `alembic check` — fails if the models and the database have drifted
- `alembic current` / `alembic history` — where a database is, and what exists
- `alembic downgrade -1` — step back one revision

Three things worth knowing:

- **Every table module must be imported in `app/models/__init__.py`.** Autogenerate walks
  `SQLModel.metadata`, and a table nobody imported is invisible to it — the migration comes
  out empty and the omission is silent.
- **The URL comes from `app.config`, not `alembic.ini`.** That file goes through
  configparser, where a password containing `%` fails on interpolation.
- **`script.py.mako` imports `sqlmodel`.** SQLModel emits `sqlmodel.sql.sqltypes.AutoString`
  for `str` columns, and the stock template doesn't import it, so the generated migration
  fails with `NameError` at upgrade time.

## Environment

`.env` is gitignored; `.env.example` documents every name. `SECRET_KEY` is generated with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`. The R2 keys come from the
Cloudflare dashboard (Object Read & Write, scoped to the `fortu-cms` bucket) and are entered
locally and in Railway's variables — never committed.
