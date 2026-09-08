# Frontend Requirements — Fortu CMS

Architecture rules for the Vue frontend. These are binding: if a change cannot be made
without breaking one of them, the rule gets discussed and updated here first, not worked
around in code.

---

## 1. Stack

| Concern | Choice |
|---|---|
| Build tool | **Vite** |
| Framework | **Vue 3** (`<script setup>`) |
| Language | **TypeScript** — no plain `.js` files |
| Styling | **Tailwind CSS v4** — utilities in templates, tokens in `src/style.css` |
| Router | Vue Router |
| State | Pinia, for shared state only |

---

## 2. Layers

Four layers, each with one job. Dependency runs one way:

```
View  →  Container  →  Hook  →  API hook  →  fetch
  ↘         ↘            ↘
   router    Reusable     Store (Pinia)
```

| Layer | Lives in | Named | May contain |
|---|---|---|---|
| **View** | `src/views/` | `<Name>View.vue` | Layout + `<router-view>` outlets. The router points here, and nowhere else. |
| **Container** | `src/containers/` | `<Name>Container.vue` | A feature. Calls hooks, routes, handles events. |
| **Reusable** | `src/reusables/` | `<Name>.vue` | Generic pieces. Knows nothing about media, playlists or devices. |
| **Hook** | `src/hooks/` | `use<Name>.ts` | State, transforms, business rules. Owns loading and error state. |
| **API hook** | `src/api/` | `use<Domain>Api.ts` | HTTP only — call, parse, type, return. |
| **Store** | `src/stores/` | `use<Name>Store.ts` | Pinia. Cross-container shared state only. |

### The TypeScript rule, stated plainly

> TypeScript lives in **containers** or **hooks** — nowhere else.

- **Views**: template and layout only.
- **Reusables**: props and emits; no fetching, no router.
- **Containers**: hooks, routing, event handlers. No `fetch`, no stores, no data shaping.
- **Hooks**: business logic and state.
- **API hooks**: transport. No loading refs, no formatting, no defaults.
- **Stores**: state. Never HTTP.

**Containers do not import stores directly** — they go through a hook (`useAuth()` wraps
`useAuthStore()`), which keeps the container rule to one thing: call hooks.

---

## 3. Auth

- Enforced **once, in a router guard**, never per container.
- The session is an **HttpOnly cookie**, so JS can never read it. "Am I signed in?" is
  always answered by `/me` returning 200 vs 401 — never by inspecting storage.
- The guard resolves the user before the first navigation, so a reload or a deep link lands
  on the right page instead of flashing the login screen.
- Routes opt out with `meta: { public: true }`; owner-only routes use `meta: { ownerOnly: true }`.
- **Hiding a nav entry is a courtesy, not the control.** The server refuses these routes
  regardless, and the backend check scripts prove it independently of this app.
- Every request sends `credentials: 'include'`. The backend must list the frontend's origin
  in `FRONTEND_ORIGIN` / `EXTRA_CORS_ORIGINS`, and **`localhost` and `127.0.0.1` are
  different origins to a browser** — a mismatch shows up as a bare CORS error naming
  neither.

---

## 4. Design system

Taken from **fortu.co.id** by reading its computed styles, not by eye. Tokens live in
`src/style.css`; that file is the design.

| Token group | Value | Notes |
|---|---|---|
| Font | `"Helvetica Neue", Helvetica, Arial` | One family, no webfont to load |
| Heading weight | **500** | Medium, never bold — at every size |
| Heading tracking | **-0.025em** | Applied once to `h1..h4` in `style.css`, so no component has to remember it. The single most recognisable property of the brand. |
| `canvas` / `surface` / `raised` | `#ffffff` / `#f9f9f9` / `#f2f2f2` | page → card → inset |
| `ink` / `ink-muted` / `ink-subtle` / `ink-inverse` | `#101111` / `#7d7d7d` / `#a8a8a8` / `#f9f9f9` | |
| `line` / `line-strong` | `#e5e5e5` / `#bfbfbf` | dividers, and outlines on controls |
| `danger` | `#9b2c2c` | **The one non-monochrome token**, for destructive actions and errors only |
| Radii | 4 / 6 / 8 / 12 / 16 px, plus the pill | |
| Motion | `cubic-bezier(0.4, 0, 0.2, 1)`, 150ms / 200ms | one curve, two durations |

**Light mode only.** There is no dark palette and no runtime theming. `color-scheme: light`
is declared so native controls follow.

**There is no accent hue, and that is the defining constraint.** Nothing marks "active" with
colour, because there is no colour to mark it with. Selection, focus and primary actions are
expressed with **ink fill and weight**: a selected nav row is ink on `raised`; a primary
button is solid ink; focus is a darker line. Introducing a hue to signal state would break
the language rather than extend it.

Three rules that follow from the source design:

- **Buttons are pills carrying a 2px border, in every variant.** Solid and outline share one
  silhouette, so they sit side by side without appearing to shift size.
- **Cards carry no border, and nothing has a shadow.** The surface tint separates a card from
  the page; an outline on top of it says the same thing twice and turns a stack of cards into
  a grid of boxes. An interactive card therefore cannot signal hover on its edge — it deepens
  its surface instead.
- **Borders are for controls and dividers**, not for wrapping things. An input needs a
  visible target before it is focused; the sidebar's right edge is a line *between* two
  things. Neither is an outline *around* something.

---

## 5. Backend contract

Base URL from `VITE_API_BASE_URL` — local `http://localhost:8001` (**not 8000**), production
the Railway domain.

| API hook | Wraps |
|---|---|
| `useAuthApi` | `GET /me`, `POST /auth/login`, `POST /auth/signup`, `POST /auth/logout` |
| `useMediaApi` | Phase 5–6 |
| `usePlaylistApi` | Phase 7 |
| `useDeviceApi` | Phase 8–9 |
| `useUserApi` | Phase 9b |

Response types live in `src/types/api.ts` and mirror the backend's Pydantic models.

---

## 6. Screens

| Route | View | Containers |
|---|---|---|
| `/login`, `/signup` (public) | `LoginView` | `AuthContainer` |
| `/media`, `/media/:id` | `SidebarView` | `SidebarContainer` + media containers |
| `/playlists`, `/playlists/:id` | `SidebarView` | + playlist containers |
| `/devices`, `/devices/:id` | `SidebarView` | + device containers |
| `/settings/users` (owner only) | `SidebarView` | + `UserListContainer` |

`/` redirects to `/media` — the library is what you open the CMS to work in. The **player is
not a route here**; it is the separate Android app.

---

## 7. Running it

```bash
cd frontend && npm install
```

```bash
cd frontend && npm run dev
```

The backend must be running on **8001** and its `FRONTEND_ORIGIN` must match, or CORS blocks
every request.

---

## 8. Open questions

1. **Mobile layout.** Below `lg` the sidebar is hidden and nothing replaces it yet. The CMS
   is a desk tool, so this is deliberate for now — but "manage screens from your phone" is a
   plausible ask, and it would mean a top bar plus a drawer, as in strava-comp.
2. **Is `danger` allowed?** It is the one colour in a monochrome system. Deleting it and
   using ink for destructive actions is defensible; the trade is that nothing then
   distinguishes "Delete" from "Cancel" except the words.
