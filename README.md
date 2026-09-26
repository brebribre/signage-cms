# signage-cms

Digital signage: a CMS for customers, a monitoring app for Marien staff, a player for the
screens, and a marketing site.

| Folder | What it is |
|---|---|
| `backend/` | FastAPI + Postgres. The API every other app talks to. See [backend/README.md](backend/README.md). |
| `frontend/` | The CMS customers use. |
| `monitoring/` | Marien staff only: issues accounts and sets their limits. |
| `player/` | The Android player installed on screens. |
| `web-player/` | The same player in a browser, for screens that can run one. |
| `website/` | The public marketing site. |

- [ACCOUNTS.md](ACCOUNTS.md) — the three kinds of account, sub accounts, and who can do what.
- [DEPLOY.md](DEPLOY.md) — the Railway services, their environment variables, and how a deploy works.
