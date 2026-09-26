# Security review — 26 September 2026

A review of whether one customer can reach another customer's screens, and whether the platform
can be broken into. Written as a punch list to work through before real customers are onboarded,
not as a list of incidents. Production currently holds two staff accounts and no paying
customers, so nothing here is being exploited today.

**The headline.** The thing you were most worried about — one customer controlling another
customer's screens — is, with one exception, genuinely well defended. I ran 43 cross-tenant
attacks against a real instance and all 43 were refused. The exception is serious and is the
first item below: **any customer can force an app build onto every screen on the platform.**

Separately, and unrelated to tenants: **one malformed web address kills any of the four public
sites**, and there is **nothing at all slowing down password guessing**.

## How this was tested

Not by reading alone. Five reviewers read the code in parallel, and every finding below was then
confirmed by hand before it was written down:

- **43 live cross-tenant attacks** against a real instance, with one customer account attacking
  another, plus a sub account attacking its own account's screens.
- **Live proof of the rollout finding**, including another customer's screen being handed a build
  chosen by the attacker, and a customer deleting a rollout Paskall had scheduled.
- **A live crash test** of the web server on a throwaway port, not production.
- **Live checks against production** for rate limiting, security headers, the API doc surface,
  CORS, and the deployed configuration.
- **Git history** searched for secrets that were ever committed, and the broker's committed
  password hashes checked against the live passwords.

Anything reasoned rather than executed says so. The cross-tenant attack probe was written as a
throwaway for this review; it is worth keeping as a permanent `scripts/check_*.py` regression test
if you want the 43 attacks re-run on every change.

## Findings

| # | Finding | Severity | How confirmed |
|---|---|---|---|
| C1 | Any customer can push an app build to every screen on the platform | **Critical** | Live, twice |
| H1 | One malformed web address kills any of the four sites | **High** | Live, locally |
| H2 | Nothing slows down password guessing on either sign-in | **High** | Live, production |
| H3 | The sign-in form is also a cheap way to exhaust server memory | **High** | Reasoned |
| H4 | Signing out does not end the session | **High** | Live |
| H5 | Upload size is never enforced, so quotas are bypassable | **High** | Read |
| M1 | Scene websites may point at internal addresses | Medium | Read |
| M2 | The app a screen installs is checked only by its byte length | Medium | Read |
| M3 | A customer-app cookie opens the staff API | Medium | Live |
| M4 | One customer can test whether a username exists anywhere | Medium | Live |
| M5 | Nothing refuses the published default signing key | Medium | Config checked |
| M6 | Sub-account screen limits on schedules and campaigns are single-layer | Medium | Read |
| M7 | A sub account can drive and delete a screen with no review | Medium | Read |
| M8 | The pairing limit is per-person and resets on restart | Medium | Read |
| M9 | Starting a pairing is unauthenticated with no ceiling | Medium | Read |
| M10 | No security headers on any site | Medium | Live |
| M11 | The interactive API docs are open to the world | Medium | Live |
| M12 | Customers can see the platform build list and rollout timeline | Medium | Live |
| M13 | Some list and text fields have no size limit | Medium | Read |
| M14 | Scene websites are framed with weak or no sandboxing | Medium | Read |
| M15 | Backend dependencies are unpinned with no lockfile | Medium | Read |
| L1–L13 | Smaller items, listed below | Low | Mixed |

---

## Critical

### C1. Any customer can push an app build to every screen on the platform

**Where:** [`backend/app/api/routes/player_rollouts.py`](backend/app/api/routes/player_rollouts.py), lines 34, 46, 56 and 71.

All four rollout endpoints are guarded by `RequireOwner`. That is the wrong "owner". As
[ACCOUNTS.md](ACCOUNTS.md) says in its own note on the word, an *owner account* is Paskall
itself, but the *owner role* is the main user of **every** account, including every ordinary
customer. The guard these endpoints want is `RequireStaff`.

Three things line up to make this reach other customers:

1. The guard admits any customer's main user.
2. The rollout table has no account column at all.
3. The "what should screens run" query is platform-wide, and every screen's check-in reads that
   same single row.

**What I confirmed, signed in as an ordinary customer with no staff rights:**

| Request | Result |
|---|---|
| List every published build | 200, five builds with versions and sizes |
| Read Paskall's rollout timeline | 200 |
| Schedule a build platform-wide | 201 Created |
| Another customer's screen then checks in | Told to install that build, with a working download link |
| Delete a rollout Paskall scheduled for tomorrow | 204, the row was gone |

The fourth row is the one that matters. A screen belonging to a completely different customer was
handed a version chosen by the attacker, with a signed download link.

**What an attacker gains.** They cannot upload their own app: publishing is a script run by hand,
and upload paths always sit under a per-account prefix with slashes stripped, so a customer
cannot write into the app folder. What they can do is force any *previously published* build onto
every screen. The damage is a forced downgrade. Pick an old build, and every screen on the
platform installs it. If the chosen build is signed with a different key than a screen is
running, Android refuses the install and the screen retries in a loop. That is a remote,
persistent outage on other customers' public advertising screens, from an ordinary customer
account. They can also cancel a security update you have scheduled, which is how a fix gets
quietly prevented from shipping.

**Why it is cheap to fix.** Neither the CMS nor the monitoring app calls the write endpoints; the
real path is a command-line script. So changing the guard costs nothing in the interface.

- Change `RequireOwner` to `RequireStaff` on all four endpoints.
- Make the cancel path refuse a row the caller has no business touching, rather than trusting the
  id in the address. The table is deliberately platform-wide, so the guard is the entire defence.
- Decide separately whether customers should keep seeing the build list, which the per-screen
  version picker does use. See M12.

---

## High

### H1. One malformed web address kills any of the four sites

**Where:** line 50 of [`frontend/server.mjs`](frontend/server.mjs), and the same line in the monitoring, web player and
website servers.

Each server decodes the address of every incoming request. Decoding a stray percent sign throws,
the throw is not caught anywhere in the file, and Node exits when a request handler throws.

**Confirmed on a local copy, not production:**

```
GET /    -> 200      server healthy
GET /%   -> 000      connection died mid-request
GET /    -> 000      process gone
```

One request, no account needed, and the process is dead. Railway restarts it, so a loop is a
sustained outage. All four sites share the code, including the web player origin that every
browser-based screen loads from.

**Fix:** wrap the decode in a try/catch and answer 400, and add a top-level handler so an
unexpected throw cannot take the process down. Four near-identical files.

### H2. Nothing slows down password guessing on either sign-in

**Where:** [`backend/app/api/routes/auth.py:29`](backend/app/api/routes/auth.py) and [`backend/app/api/routes/admin.py:49`](backend/app/api/routes/admin.py).

There is no counter, no delay, no lockout, and no log line when a sign-in fails. I sent six wrong
passwords in a row to the live API and got six identical refusals with no throttling.

The only rate limit in the whole codebase is on screen pairing. So the pattern exists and was
applied there, and then not to the two endpoints that take passwords.

The one real brake is the password hashing, which is deliberately slow. That holds the rate down
to tens of guesses a second rather than thousands. Against a password that only has to be 8
characters (L6), handed over by staff in a chat message, that is still enough to work through a
common-password list in hours, unnoticed, because nothing is logged. The staff sign-in is the
same code, and it reaches every customer account.

The "Reset password" link on the sign-in page signs in first, so it has the same gap.

**Fix:** count failures per account, slow down or lock after a handful, and log them. Put the
counter in the database, for the reason the pairing limiter's own comment gives: an in-memory one
survives neither a restart nor a second server. Note that per-address limiting needs more care,
because the proxy means the backend cannot currently see the real caller's address.

### H3. The sign-in form is also a cheap way to exhaust server memory

Passwords are hashed with argon2id, which is the right choice. Its settings are the library
defaults, and one of those is the interesting part:

| Setting | Value |
|---|---|
| Memory per check | 64 MiB |
| Passes | 3 |
| Threads | 4 |

Every sign-in attempt allocates 64 MiB. An attempt against a username that does not exist
allocates it too, because the code deliberately burns the same work to avoid revealing which
usernames are real. That trade-off is correct and worth keeping, but it means an unauthenticated
stranger can make the server allocate 64 MiB per request with no account and no valid username.
The backend runs as a single process, so a few dozen simultaneous attempts are enough to exhaust
a small container.

**This one I did not test**, because testing it means taking production down. It follows from the
settings and the absence of any rate limit, both of which are confirmed.

**Fix:** the rate limiting in H2 closes this too. Do not lower the memory setting; that weakens
the hashing to fix the wrong problem.

### H4. Signing out does not end the session

**Where:** [`backend/app/api/routes/auth.py:43`](backend/app/api/routes/auth.py).

Signing out only asks the browser to drop its copy of the cookie. The cookie itself stays valid
for its full 30 days. Confirmed: sign in, sign out, replay the old cookie, and the server still
answers 200 and says who you are.

The system already has working revocation, a version number on each user that invalidates old
cookies. Changing a password bumps it and that works properly. Signing out just does not use it.

This is a product used on shared machines and in venues. Someone signs out on a borrowed laptop
and reasonably believes it is over. Anyone holding the cookie can keep acting as them for a
month, and the only way to stop it is a password change.

**Fix:** bump the version on sign-out. One line, to a mechanism that already exists.

### H5. Upload size is never enforced, so quotas are bypassable

The signed upload link commits to the file type but says nothing about size. The size and quota
checks both run against a number the browser supplies, and nothing checks it again at the storage
layer.

Two consequences:

**Free unlimited storage in your bucket.** Declare a 1-byte upload, then upload 5 GB to the link.
The finish step catches the mismatch and refuses, so the file never appears in the library — but
the 5 GB is already stored. The record stays in a pending state, which means it is never counted
toward the quota and never shown. Worse, the cleanup script builds its list of known files from
*every* record including pending ones, so it will never collect the file either. The storage is
unreclaimable and the loop can repeat.

**Quota bypass.** The quota check counts only finished files, and nothing re-checks at the end.
Fire many uploads at once, each declaring a size just under the limit, and they all pass the
check before any of them finish.

**Fix:** either use an upload policy that pins a size range, or reserve the declared bytes against
the quota when the upload starts and delete both the object and the record when the sizes do not
match.

---

## Medium

### M1. Scene websites may point at internal addresses

A scene can hold a live website. The check requires only that the address be https with a host,
so `https://localhost:8001/…`, `https://127.0.0.1/`, `https://10.0.0.7/` and
`https://metadata.google.internal/` are all accepted. The browser-side helper does require a dot
in the host, but that is bypassed by calling the API directly.

The backend never fetches these addresses itself, so this is not the classic server-side request
problem. The fetch happens on the screen, inside the venue's own network, and in the browser of
every CMS user who opens that playlist, including the client reviewing a sub account's change.
Session cookies are not sent and responses cannot be read back, so this is reach and display
control, not data theft. On a signage screen the framed page is the entire display.

**Fix:** refuse loopback, link-local, private and internal hosts, and refuse the app's own
addresses.

### M2. The app a screen installs is checked only by its byte length

The update instruction a screen receives carries a version, a link, a size and a timestamp. There
is no checksum, and the installer checks only that the downloaded file is the expected number of
bytes before handing it to Android.

Media files do carry a checksum. The one file that becomes running code does not.

The real protection is Android's rule that an update must be signed with the same key as the
installed app. That is doing all the work. It is weaker than it looks, because the build setup
silently falls back to the debug signing key when the real keystore is absent, and some screens
are known to be carrying debug-signed builds.

**Fix:** send a checksum with the update and verify it before installing.

### M3. A customer-app cookie opens the staff API

Both sign-ins issue the same kind of cookie, and staff status is looked up from the database
rather than carried in the cookie. So a cookie minted by signing into the **customer** CMS is
accepted by the **staff** API. Confirmed: sign in at the customer sign-in, call the staff accounts
endpoint, and it returns every account on the platform.

This only matters for your own team, since a customer's cookie is refused by the staff check. But
it means that for staff, being signed into the customer CMS *is* being signed into the platform
admin API. One scripting bug or one bad dependency in the customer-facing app, running in a staff
member's browser, can call the staff API with their session and reset any customer's password. It
never needs to read the cookie, which is protected from scripts; it just makes requests that
carry it.

Making it worse, the CMS's own proxy forwards everything under `/api/` to the backend with no
filter, so the staff API is reachable from the customer address.

Notably the project already understands this risk and defends against it locally, by putting the
monitoring app on a different hostname in development on purpose. The production setup quietly
undoes that.

**Fix:** give the staff session its own cookie name and signing salt, or mark in the token which
app issued it and check that in the staff guard. Separately, have the CMS proxy refuse
`/api/admin/*`.

### M4. One customer can test whether a username exists anywhere

Creating a sub account answers 409 "That username is taken" when the name exists **anywhere on
the platform**, because usernames are globally unique. Confirmed: probing a username belonging to
another customer returns 409, an unused one returns 201.

The sign-in endpoint is carefully built not to leak this, and I confirmed that too: a real
username and a made-up one produce identical refusals. This route undoes that work from another
direction. On its own it is a privacy leak. Combined with H2 it is the missing first step, since
confirming a real username is what makes unlimited guessing worth starting.

### M5. Nothing refuses the published default signing key

The session signing key defaults to a fixed string committed to what is a **public** repository.
There is no startup check. If the environment variable is ever missing, the app boots happily and
signs cookies with a key anyone can read, which means anyone can mint a cookie for any user,
including staff.

**Checked:** production has a proper 64-character key set, so this is not live today. It is a
missing guardrail on a hole that would be total, and the deploy notes already document a failure
mode where a variable looks set but never reaches the container.

**Fix:** refuse to start with the default key whenever secure cookies are on.

### M6. Sub-account screen limits on schedules and campaigns are single-layer

A sub account is meant to reach only the screens it was given. That is enforced properly wherever
a screen is addressed directly. But the two objects that *contain* a screen reference, schedules
and campaigns, are looked up by account only, with no check of the screen grants.

What saves it today is that every screen-affecting change by a sub account is parked for the
client's approval, and the approval screen honestly names the screens affected. So there is no
unapproved cross-screen change. But on approval, the schedule and campaign paths do not re-check
the screen grants, while the paths that address a screen directly do. The protection is one layer
deep, and that layer is the review queue rather than the permission check.

### M7. A sub account can drive and delete a screen with no review

The review queue covers what *plays*. It does not cover:

- Pinning a scene live on a screen. The limit is four hours, but re-issuing restarts the clock, so
  a loop makes it permanent.
- Switching the screen off through the power override.
- Changing the PIN that stops someone walking up and leaving the player.
- Disconnecting or deleting the screen entirely.

The last one is worth thinking about together with the pairing findings: deleting a screen sends
it back to displaying a fresh pairing code in a public place, which is the state in which it is
easiest for someone else to claim.

**Fix:** decide deliberately which of these belong behind review, and at minimum make disconnect
and delete owner-only.

### M8. The pairing limit is per-person and resets on restart

Claim attempts are limited to ten a minute, counted in memory against each **user**. Sub accounts
can be created freely, so an attacker can spread attempts across many of them, and the counter
resets on every deploy.

The codes themselves are strong: six characters from a 31-letter alphabet is about 887 million
combinations, valid 15 minutes. Guessing a *specific* screen's code is not realistic. What the
multiplier buys is opportunistic guessing against whatever happens to be pending anywhere, run
continuously. Each hit is a real screen joining the attacker's fleet.

**Fix:** count against the account rather than the person, keep the counter in the database, and
add an overall ceiling.

### M9. Starting a pairing is unauthenticated with no ceiling

Anyone can ask for a pairing code, repeatedly. Each call writes a row and runs a cleanup sweep.
Being unauthenticated is correct, since a screen has no credential yet. Having no ceiling is not:
it is a cheap way to fill the table, and every extra pending code improves the odds for the
guessing in M8.

### M10. No security headers on any site

None of the CMS, the monitoring app, the web player, or the API sets a content policy, frame
protection, strict transport, or content-type-sniffing protection. Confirmed live on all three
public sites. Nothing sets headers in any of the four Node servers.

Most directly, nothing stops the apps being embedded in a frame on someone else's site, which is
the setup for tricking a signed-in user into clicking something. A content policy would also be
the second line of defence behind M3 and M14.

### M11. The interactive API docs are open to the world

`/docs`, `/redoc` and `/openapi.json` all answer 200 to anyone, and the API root redirects to the
docs. This hands a stranger the complete list of endpoints, including every staff route, and the
exact shape of every request. The source is public anyway, so little is secret here; what it
removes is the effort of finding the interesting endpoints before trying C1 and H2.

### M12. Customers can see the platform build list and rollout timeline

The same wrong guard as C1 also exposes reads. Any customer can list every app build ever
published, with sizes and dates, and read the full rollout timeline including anything scheduled
for the future. The build list is used by the per-screen version picker, so narrowing it needs a
moment's thought. The timeline has no customer use at all.

### M13. Some list and text fields have no size limit

Playlists correctly cap their scenes and elements. Campaigns do not cap either their screen list
or their rule list, and creating a campaign does one lookup and one insert per rule per screen in
a single request. A campaign with one screen and two hundred thousand rules is accepted.

Separately, the screen check-in caps the *number* of error strings at twenty but not the length of
each, and the reported-settings object has no cap at all. There is no overall request size limit
anywhere in the stack.

### M14. Scene websites are framed with weak or no sandboxing

The CMS preview frames use a sandbox setting pair that effectively disables the sandbox whenever
the framed page is same-origin, and a customer can make it same-origin by pointing a scene at the
CMS's own address. Today the framed page would be the CMS's own code rather than attacker
content, so this is not an injection path — it removes the last barrier rather than crossing it.

The web player frames scene websites with **no sandbox at all**, so a framed page can navigate the
whole screen somewhere else permanently. The Android player's web view similarly has no
navigation filter.

**Fix:** drop same-origin from the CMS preview sandbox, add a sandbox to the web player frame that
withholds top-level navigation, and refuse a scene website pointing at the app's own addresses.

### M15. Backend dependencies are unpinned with no lockfile

Every backend dependency is a floor with no upper bound, and there is no lockfile. Deploys happen
automatically on every push, so a change to the marketing site can rebuild the backend against
different library versions, and "what is running in production" is not answerable from the
repository. It also means a compromised release enters production automatically.

No specific vulnerable version can be named, precisely because there is no version to assess.
That absence is the finding. The image libraries deserve particular attention, since they parse
uploaded files including iPhone images, in the same process as the API.

The four frontend apps already do this correctly, with committed lockfiles and current versions.

---

## Low

**L1. Live broker password hashes are in the public repository.** The broker's seed file, which is
tracked in git, contains the stored password hashes for the admin and publisher accounts. I
verified mathematically that these are the **live** credentials, not samples. The saving grace is
that both passwords are 31 and 32 random characters, so even at the file's weak iteration count
they cannot realistically be cracked. Rotate as hygiene and stop tracking the file, injecting it
at container start the way the TLS private key already is. Not urgent.

**L2. CORS names an old generated domain, not the real ones.** The one allowed origin is a
generated Railway hostname; the real addresses are not listed. I checked, and that hostname still
serves your own app, so nothing is exposed today. Nothing breaks either, because both apps reach
the API through their own address rather than across origins. The risk is only if that domain is
ever detached and the name recycled.

**L3. Play-event filenames are resolved without an account filter.** The lookup turning a file id
into a filename has no account condition, where every comparable query does. A customer
controlling their own screen's token could report another account's file id and read the filename
back. They would need to already know an unguessable id, so it is a narrow oracle rather than a
way to browse. One clause fixes it.

**L4. Screen names leak through the review queue.** A screen's name is looked up with no grant
check and returned in the response, so a sub account could learn the name of a screen it was not
given. Same account only.

**L5. The pairing poll token travels in the web address.** That token is the one secret that
exchanges for a screen's real credential. Putting it in the path means it lands in access logs
and proxy logs. Anyone who can read logs during a pairing window could collect the credential
first, and the real screen would just appear to hiccup and re-pair. Move it to a header or body.

**L6. Passwords only have to be 8 characters**, with no other rule and no check against known
breached passwords. This is what makes H2 worth an attacker's time.

**L7. An owner resetting a sub account's password leaves no record.** The staff-side reset is
logged and deliberately does not record the value, which is right. The owner-side one logs
nothing, which muddies who actually did a thing afterwards.

**L8. The screen PIN is stored and sent in plain text, with no lockout.** The plaintext is a
deliberate, documented trade-off: the screen needs the digits to compare. But the on-screen check
has no attempt limit, so a four-digit PIN falls to patience from someone standing at the screen.
With no PIN set, leaving the player needs nothing at all.

**L9. One setting quietly doubles as the "this is production" flag.** The secure-cookie setting
also switches off the development pairing bypass. Forgetting it does two unrelated bad things at
once, and the warning it logs does not fire in the case you would care about. Give production its
own explicit flag.

**L10. Broker credentials are never revoked.** There is provisioning code but no removal code. A
deleted screen keeps working broker credentials for its own topic forever, and the broker's client
list grows without bound. The impact is near zero, because that topic carries only a
"something changed" nudge, but it is a revocation gap.

**L11. Conversion errors are returned to the customer verbatim**, including the tool's own error
text and temporary file paths, and storage errors naming the bucket and key. Store the detail,
show a short message.

**L12. The static file guard is a text prefix test, not a folder boundary test.** Real directory
traversal is correctly blocked, and the decode-then-join order is right, which is the part most
projects get wrong. But a sibling folder whose name merely starts with the same letters would pass.
Not exploitable today. One character fixes it.

**L13. The Docker ignore file does not exclude environment files or keys.** Nothing leaks today,
because the only build using the repository root copies just the website. A future change could
bake secrets into an image layer.

## Not security, but fix it before it bites

The orphan cleanup script builds its list of known files without including the converted video
copies. Any video with a separate playback copy would therefore be treated as an orphan and
deleted if that script is ever run with the delete flag. That is real data loss on live content,
and the script is dry-run by default today, which is the only reason it has not happened.

---

## What is solid

Worth knowing so none of it gets traded away by accident.

**Tenant isolation holds.** 43 attacks from one customer against another were all refused:
reading, renaming and deleting screens, playlists, media and campaigns; putting another
customer's playlist on a screen; putting another customer's file in a playlist; aiming a campaign
or schedule at another customer's screen; forcing a disconnect; pushing live content; power
commands. Each returns "not found" rather than "not allowed", so nobody can use the error to work
out what exists elsewhere.

**Screens cannot reach each other.** A screen's token can call exactly three endpoints, and none
takes an id. The screen is always identified by its own credential, so there is no parameter to
tamper with. That is structurally safe, not safe by a check someone remembered.

**The message broker is correctly partitioned.** Each screen gets its own credentials, and the
device role is subscribe-only, restricted to a topic containing the screen's own id. A screen
cannot listen to another's topic and cannot publish at all. Both clients verify the broker's
certificate against a pinned copy rather than trusting any certificate.

**The broker carries no authority.** The push payload is ignored by the player; it means only
"check in now", and every real decision is re-fetched over an authenticated connection. So even a
fully compromised broker cannot change what a screen shows. This is the single best decision in
the system and it should be preserved deliberately.

**Pairing uses two secrets.** The human-readable code is for typing; a separate 256-bit token is
what exchanges for the real credential, and it is minted at collection rather than at claim time,
which is what makes storing only a hash meaningful. A code read off a screen cannot be turned into
a credential.

**Session handling is well built.** The cookie carries only a user id and a version number.
Role, account, active status and expiry are read fresh from the database on every request, which
is why deactivating someone takes effect on their next call. Expiry is enforced from inside the
signature, so the holder cannot extend it. Tampered and unsigned cookies are refused; I tested all
three cases.

**No privilege escalation through request bodies.** No request shape anywhere accepts an account,
a role, a creator or an account kind. Roles are set in code at both places a user is created. I
tried to create a user in another account with an injected role and account, and got an ordinary
sub account in my own account.

**The approval system is built correctly.** This is the part that usually breaks. A parked change
is replayed as the person who requested it, not the approver, so their own limits apply again, and
the payload is re-validated through the same checks rather than trusted. It re-verifies the
requester is still active and still in the account. If applying fails, the review stays pending
with the reason rather than being marked approved for something that did not happen.

**Password handling is careful.** argon2id, with the cost re-checked on every sign-in so it can be
raised later. Unknown usernames burn the same work as real ones, so sign-in does not reveal which
accounts exist, and I confirmed the refusals are identical. A refused staff sign-in is
indistinguishable from a wrong customer password. Changing your own password requires the current
one, even just after signing in, and a password someone else chose is temporary and cannot be used
for anything but choosing a new one.

**No injection surface.** No raw SQL beyond a fixed health check. No shell invocation anywhere;
the video tools are called with argument lists and server-generated filenames, so an uploaded
file's name never reaches a command. No unsafe HTML rendering in the CMS or monitoring app, and
the two places the web player builds HTML both escape every value.

**Uploads cannot become scripts.** The upload link commits to the file type, the allowed list
deliberately excludes the one image format that can carry script, and files are served from
storage rather than from any app address, so uploaded bytes can never run as part of the CMS.

**Storage keys cannot escape their account.** The key is built server-side from the signed-in
account plus a fresh id, with slashes stripped from the filename, and there is exactly one place
that signs an upload. This is also what stops C1 from becoming arbitrary code execution.

**No secret has ever been committed**, which matters because the repository is public. No
environment file appears anywhere in the history and no private key was ever committed; a full
scan of every object in history came back clean. The two certificate files that are tracked are
public certificates. Production has a proper signing key, secure cookies, and same-site cookies
set, and the development pairing bypass is switched off.

**The production runtime has no third-party dependencies.** All the web servers are hand-written
with the reasoning recorded, and the frontends commit lockfiles with current versions.

**Nothing sensitive is logged.** No token, password or cookie reaches a log, database statement
logging is explicitly off, and the password-reset audit line deliberately records who, not what.

---

## What was not covered

- **The live broker's rules were read from the file in the repository.** The running broker keeps
  its own copy on a disk that has been up a while, so confirm the live rules still match, and that
  wildcard subscriptions are refused.
- **No automated dependency vulnerability scan was run**, and with nothing pinned there is no
  version set to scan.
- **The memory-exhaustion finding (H3) was reasoned, not tested**, because testing it is an outage.
- **Which live screens are debug-signed was not determined**, and that decides how much of M2's
  remaining protection actually holds.

## Suggested order

1. **C1** — change the guard on four endpoints and scope the cancel path. The only finding that
   lets one customer touch another's screens.
2. **H1** — one try/catch in four files. Smallest fix here, and right now one request takes a site
   down.
3. **H2 and H3** — rate limit both sign-ins and log failures. One change closes both.
4. **H4** — bump the session version on sign-out. One line.
5. **H5** — pin the upload size, or reserve and clean up.
6. **M5, M11** — refuse the default key at startup, close the public docs.
7. **M1, M14, M10** — the scene-website host rules and the framing rules belong together.
8. **M3** — separate the staff cookie, and stop the CMS proxy forwarding the staff API.
9. **M2, M8, M9** — the screen-side items: checksum the app, harden pairing.
10. **M6, M13, L3** — the missing checks and the missing limits.
11. The remaining Low items, and the orphan-cleanup bug before that script is ever run for real.

Everything below C1 and H1 is ordinary pre-launch hardening. C1 should be closed before a second
customer account exists, and H1 before anyone is relying on the sites being up.
