# CMS UX Redesign — Planning Doc

Draft for revision — not a spec yet. Where I'm genuinely unsure which way to go, I've written
both options rather than picking one for you. Everything here is a proposal to react to, not a
decision already made.

---

## 1. The problem, concretely

The current navigation is: **Media / Playlists / Campaigns / Devices / Health / Settings**. That
list is not a set of user goals — it's the app's database tables, one nav item per SQLModel
class. That's not automatically wrong (plenty of good tools are basically a CRUD UI over a
schema), but it starts costing real clarity once a task requires knowing how those tables relate
to each other, and the UI never tells you.

Concrete symptoms, from actually walking the current app:

- **"Why is this screen showing what it's showing" has no good answer.** It's answered on Device
  Detail's Manage tab, by `DeviceNowPlayingContainer` — one card, one device at a time — and even
  that card doesn't render `valid_until` (the API returns it; the component just never displays
  it). So today you cannot tell, without doing the math yourself, when the current answer stops
  being true.
- **Campaigns hides its own coverage gaps.** The Campaigns list shows `{device_count} screens ·
  {rule_count} rules` per campaign — a count, not names. There's no view anywhere that answers
  "which of my screens are covered by *no* campaign and are quietly just playing their bare
  default?" That's exactly the kind of thing that goes unnoticed until someone complains that a
  screen in the corner has been showing the wrong thing for a week.
- **The same fact — what a screen is playing right now — is edited in one place and viewed in
  two others, disconnected.** The Devices list shows a read-only "now playing" chip per row (with
  an explicit code comment: *"what this screen plays is decided in Campaigns, not here"*). Device
  Detail shows it again, slightly differently, with no link back to whichever campaign is
  actually responsible. Campaigns is where you'd go to change it. Three surfaces, one fact, no
  cross-links between them.
- **Media usage is one click deeper than it should be.** You can see which playlists use a file,
  but only after opening that file's detail page — the library grid itself gives no hint before
  you click delete and get a 409.
- **Roles are binary in the UI but not in the data.** The frontend only knows `isOwner` — it hides
  two sidebar links and gates two routes. The backend already scopes a manager to specific
  devices via `DeviceAccess` (campaigns' `_reachable_device_ids` respects it). Nothing in the UI
  today explains that scoping to a manager who hits it — they'd just find some devices missing
  with no stated reason.

None of this is really about visual design. It's information architecture: **the primary
structure of the app mirrors its tables instead of the questions people actually ask.**

---

## 2. The principle for the redesign

> Organize the primary navigation and page structure around the *questions someone is trying to
> answer* or *tasks they're trying to do*, not around what's in the database. Then, once you're
> on the page for a task, surface exactly the facts (including the "boring" data-model facts —
> priority, expiry, scope) needed to make the answer trustworthy, right there, not behind a click.

That second half matters as much as the first — this is not "hide the data model," it's "stop
using the data model as the *map*, and start using it as *evidence*, placed exactly where the
question comes up." A schedule's expiry, a device's manager-scope, a media file's usage count —
these are all "boring data model facts," and all of them should be *more* visible than they are
today, just not as their own top-level pages.

A concrete before/after, using the most common real task — "why is the lobby screen showing the
wrong thing on a Friday afternoon, and how do I fix it":

- **Today**: open Devices, find the screen, open it, read the now-playing card (which doesn't say
  until when), guess it's a schedule, go to Campaigns, open each campaign, check which one
  targets this device and covers Friday, find the rule, edit it, go back to the device to confirm
  it changed (no visible confirmation of *when* it'll change).
- **Proposed**: open the screen, see "Playing **After Hours Promo** because of **Weekend
  Campaign**, until **Fri 5:00 PM**" as one line with the campaign name as a link, click through,
  fix the rule, see immediately (on the same screen's page) when the new resolution will take
  effect.

---

## 3. Proposed information architecture

Five top-level items instead of six, but reshuffled — not everything maps 1:1 to today's pages.

### Now (new)

A fleet-wide status view — effectively what today's Devices-list "now playing" column and the
Health page's stat cards both partially do, merged and made explorable. This becomes the
**landing page** instead of Media.

- Fleet summary strip: screens total, offline, reporting errors, storage — kept from Health.
- One row per screen: name, location, current resolution (**Playlist X · via Campaign Y · until
  5:00 PM** / **default, no active override**), status dot, last seen.
- Filters: offline only, errored only, "playing default only" (**this is the coverage-gap view
  Campaigns can't answer today**), by manager-scope if you're an owner looking at a manager's
  view.
- Click a row → Screen detail (below). No separate "Health" destination anymore; health *is* a
  view of Now, not a different question.

### Screens (was: Devices)

Per-screen home: identity, pairing, settings, activity — everything about *one* screen's own
configuration and history. What moves here vs. stays on Now:

- Now = "what's true across the fleet, right now, at a glance."
- Screen detail = "everything about this one screen" — including the same resolution fact, but
  now with room to also show *every* rule that could apply to it (not just the one currently
  winning), so you can see e.g. "3 rules could apply here; here's the one active now; here's what
  takes over next and when."
- Keeps: Manage (name/location/orientation/timezone), Settings (volume/power/etc.), Errors & logs.
- Adds: a "Coverage" section — every campaign/schedule that targets this device, in priority
  order, each a link.

### Rules (was: Campaigns, absorbing the standalone per-device Schedule concept)

Reframed from "a list of campaigns" to "when does what play, fleet-wide" — a calendar/timeline
surface first, a list of named rule-sets (campaigns) second.

- Default view: a week-at-a-glance timeline, one row per screen or per rule-set (open question —
  see §7), so overlapping windows and priority conflicts are visually obvious instead of
  something you have to compute by reading two campaigns side by side.
- A rule-set (today's "Campaign") is still the unit you create/edit — same rule editor we already
  built (including the date-range field), just reached from a page that also shows you the
  *effect*, not only the *configuration*.
- Explicitly surfaces "screens with no active rule-set" — the gap Campaigns hides today.

### Content (was: Media + Playlists, as one section with two tabs or a combined view)

These two are already well-connected (media detail shows "used in," the scene editor is already
good) — the main gap is that usage isn't visible until you're one click deep. Keep both as
distinct working surfaces (a media grid and a playlist/scene editor are genuinely different
tools), but:

- Show a usage badge (`used in 3 playlists`) directly on each media grid card, not just on its
  detail page.
- Cross-link the other direction too: a playlist's element picker should make it obvious which
  media are already used elsewhere, if that's ever a meaningful signal (open question).

### Settings

Roughly as-is (Users, Player updates), but:

- Extend the mobile "Updates" link pattern (already shipped) to Users too, or fold both into a
  proper mobile settings menu instead of one-off header links each time an owner-only page needs
  phone access.
- Add a visible note on Users when viewing/editing a manager: which devices they're scoped to —
  today that scoping is invisible in the UI entirely.

---

## 4. Cross-cutting patterns worth naming once, reusing everywhere

Right now, "what's this screen playing" is rendered three slightly different ways in three
places. Instead:

- **One `ResolutionChip` component**: playlist name, `via {link to rule-set}` if applicable,
  `until {time}` if applicable, else "default." Used on Now, Screen detail, and anywhere else a
  screen is referenced (e.g. inside a rule-set's device list).
- **One "coverage" concept**, computed once, surfaced in two places: which screens a rule-set
  targets (already shown), and which screens *no* rule-set targets (not shown anywhere today).
- **One manager-scope indicator**: a small, consistent badge/note wherever a manager's limited
  device set is relevant — the Users page, and arguably a banner on Now/Screens when a manager is
  the one logged in ("You can see and manage 4 of this account's 11 screens").

---

## 5. Mobile

The bottom nav is already at capacity (5 items, explicitly commented as "no room for more" in
`useNavLinks.ts`), and owner-only pages have been getting one-off header links bolted on (Player
updates just got one; Users still doesn't have one). A 5-item flat bottom bar was already a tight
fit for a data-model-shaped nav — collapsing Devices+Health into one "Now" destination and
Campaigns+Schedules into one "Rules" destination actually **reduces** the top-level count, which
gives mobile more room rather than less. Worth deciding whether that freed-up slot goes to a
proper "Settings" entry point (a small in-app menu, not the bottom bar) rather than continuing to
special-case each owner-only page in the header.

---

## 6. Explicit non-goals

Calling these out so the redesign doesn't sprawl into re-touching things that already work well:

- The **scene editor** (`SceneEditor.vue` / `PlaylistEditorContainer.vue`) — already a full-page,
  purpose-built editor, not a data-model mirror. Out of scope.
- The **media upload/dropzone flow** — already task-shaped (drag, see progress, done).
- **Auth/login** — not part of this.
- The **visual design system** (monochrome tokens, pill buttons, etc.) — this doc is about
  structure and flow, not a re-skin. A re-skin could ride along with this later, separately.

---

## 7. Open questions — need your call

1. **Rules timeline shape**: one row per *screen* (good if you mostly think "what's happening to
   THIS screen this week") or one row per *rule-set/campaign* (good if you mostly think "what is
   THIS campaign doing across its screens this week")? Possibly both, as a toggle — but which is
   the default matters for what the page feels like on first load.
2. **How literal should "Now" be as the landing page?** Replacing Media as the default landing
   page is a real behavior change for daily users — worth confirming that "what's happening right
   now" is actually the first thing people want to see when they open the CMS, versus e.g. "was
   anything uploaded/changed since I left."
3. **Merging Devices and Health into one "Now"/"Screens" split** — do you want the fleet-overview
   and the per-screen-deep-dive to be two tabs of one section, or genuinely two separate top-level
   items (closer to today, just renamed)? The doc above assumes one merged section with a list +
   detail pattern (like Campaigns already is), but that's a real structural choice, not a given.
4. **Manager-scope visibility** — how much do you want a manager to see about the parts of the
   fleet they *can't* touch? Fully invisible (current behavior, just unexplained), a visible count
   ("4 of 11 screens"), or fully visible-but-disabled (see everything, can't act on most of it)?
   Each has a different "why can't I do this" cost.
5. **Content section** — keep Media and Playlists as two clearly separate pages (closer to today,
   just cross-linked better), or actually merge them into one section with a mode switch? The
   doc above hedges toward "keep separate, just cross-link" — confirm that's right rather than a
   bigger merge.
6. **Naming** — "Now" / "Screens" / "Rules" / "Content" are placeholders for the concepts, not
   proposals to ship literally. Rename freely.

---

## 8. Suggested phasing (once the above is settled)

Roughly cheapest-and-most-valuable first, so each phase ships something usable rather than
landing as one big-bang rewrite:

1. **Ship the missing facts first, in the current IA** — render `valid_until` on the existing
   now-playing card, add the "no active rule-set" screens list somewhere reachable, add media
   usage badges to the grid, add the manager-scope note to Users. All low-risk, all valuable
   regardless of what happens to the nav.
2. **Build the `ResolutionChip` component and use it everywhere the fact already appears** —
   consolidates three renderings into one, before touching navigation at all.
3. **Introduce the Rules timeline as a new view inside Campaigns**, without renaming or moving
   anything yet — validates the concept against real data before it becomes the default landing
   experience for that section.
4. **Only then reshuffle top-level nav** (Now/Screens split, Rules rename, mobile nav
   consolidation) — the highest-risk, most visible change, done last once the pieces it's built
   from already exist and are proven.
