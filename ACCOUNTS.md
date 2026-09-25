# Accounts — who can do what

Every person who signs in belongs to an **account**. The account is the tenant: screens, media,
playlists and campaigns belong to it, never to a person. Two things decide what someone can do:

- **The kind of account** they are in — owner, admin or client.
- **Their role inside it** — the main user, or a sub account.

There is no separate "staff" flag on a person any more. It was removed on 2026-09-22 because it
could not tell Paskall apart from a technician.

## The three kinds of account

| Kind | Signs in to | Can issue | Can set limits on | Screens and storage |
|---|---|---|---|---|
| **Owner** | CMS and Monitoring | admin and client accounts | admin and client accounts | Always unlimited |
| **Admin** | CMS and Monitoring | client accounts only | client accounts only | 15 screens, 5 GB by default |
| **Client** | CMS only | sub accounts, from the CMS | nobody | Whatever staff set |

**Owner** is Paskall itself. There is exactly one, and nothing can make a second. Its limits can
never be set, so it is always unlimited.

**Admin** is one of our technicians. They get the monitoring app so they can set up and look
after customers, but they cannot create another technician and cannot raise their own limits.
Both of those stay with the owner.

**Client** is a customer. They never see the monitoring app.

A note on the word **owner**, which the system uses for two different things. An *owner
account* is Paskall itself, the kind in the table above. An *owner role* is the main user of any
account, as opposed to a sub account. They are unrelated. The monitoring app writes the role as
**Main user** for exactly that reason, so an Admin account does not appear to have an owner
sitting inside it. The CMS still says Owner to customers, where there is no account kind on
screen to confuse it with.

## Who counts as staff

Staff means the **main user** of an owner or admin account. That is the person the account was
issued to, the one whose role is `owner` inside it.

A sub account is never staff, whatever account it sits in. A technician can make sub accounts
for their own colleagues, and those people get the CMS only. This keeps one rule true
everywhere: monitoring access is something the owner hands out by issuing an account, never
something an account holder can pass on themselves.

## Sub accounts, inside a client account

A client can create sub accounts for their staff. A sub account:

- Reaches only the screens the client gave it, and any screen it connects itself.
- Can connect new screens. Those screens count against the client's limit, and the client can
  reach them too.
- Shares the account's media, playlists and campaigns. There is one library, not one per person.
- Has every change that would alter what a screen shows sent to the client for approval. Work
  that reaches no screen, such as an upload or a draft playlist, saves straight away.

Approving replays the original request as the person who sent it, with their own screen access.
So an approved change is exactly what that person asked for, never more.

## Making accounts

Accounts are issued from the monitoring app's Accounts page. There is no public signup and no
invite email: whoever issues an account hands over the username and password themselves.

The New account form shows an **Account type** dropdown when there is a real choice to make. The
owner sees Admin and Client. A technician sees no dropdown, because client is all they can
issue, and a line of text says so instead.

Picking a type fills in what that type normally gets. Admin starts at 15 screens and 5 GB.
Client starts blank, which means no limit. Both are a starting point and can be typed over. A
blank limit field always means no limit.

The list gives each account one row, in three columns: the account name, the username, and the
person's name. The account's own row carries its main user, because they are the same thing —
the person it was issued to — and anyone else in the account sits underneath, marked as a sub
account. Only the accounts that are not ordinary customers carry an **Owner** or **Admin** badge.

The Edit limits menu appears only on accounts you are allowed to touch. A technician can see the
owner and other admin accounts, but gets no actions on them.

## Passwords

Nobody keeps a password someone else chose. Whenever one person sets another's password —
staff issuing an account, staff resetting a forgotten one, or a main user making or resetting a
sub account — that password is **temporary**. At the next sign-in the CMS shows only **Choose
your own password**, and the server refuses every other request until it's done. So whoever
handed the password over never knows the one actually in use.

- **A forgotten password:** in the monitoring app, **Reset password** on the account (the same
  rule as limits decides who may: the owner for admin and client accounts, a technician for
  client accounts, nobody for the owner account). It offers a generated password to pass on. A
  main user resets a sub account's from **Settings → User management**.
- **Changing your own:** **Settings → General**, with the current password.
- **Every change signs out everywhere else.** The session cookie carries a number that goes up
  with each change, so a session opened with the old password stops working at once.
- The monitoring app shows **Temporary password** on an account whose main user hasn't chosen
  theirs yet, and the admin log records each reset — never the password itself.
- A technician on a temporary password is sent to the CMS to choose their own before the
  monitoring app lets them in.

There is still no email reset: staff or the main user are the way back in.

The rule is enforced in `backend/app/api/deps.py` (`_refuse_until_own_password`) and checked by
`scripts/check_passwords.py`.

## Accounts that expire

Any admin or client account can have an end date, shown as **Active until** in the monitoring
app. It is set in the New account form or under **Edit limits**, and a blank field means the
account never ends. The same rule as the limits decides who may set it. The owner sets it on
admin and client accounts, and a technician sets it on client accounts only. The owner account
never has one, and a technician cannot extend their own.

"Active until 30 Sep" means the account works all of 30 September and stops as 1 October begins,
in the local time of whoever picked the date. Picking a day that has already passed switches the
account off as soon as you save. Clearing the date, or picking a later one, renews it at once.

### What an expired account can still do

- Sign in to the CMS, and sign out.
- Look at everything: screens, media, playlists, campaigns, schedules, reviews, activity, limits.
- Ask a screen to check in, which only refreshes its status.

### What it cannot do

Everything else. The server refuses every change with one plain message, so it covers routes
written later too. In practice that means:

- No new screens, and no renaming, moving, updating, live control or power changes on the ones
  it has.
- No uploads, and no deleting media.
- No new or changed playlists, campaigns or schedules, so nothing new reaches a screen.
- No sub accounts added, changed or removed, and no settings changed.
- No reviews sent, approved or rejected. A sub account's change is refused outright rather than
  queued for approval.

An expired **admin** account also loses the monitoring app completely. Its main user gets a
message saying the account has expired, not "wrong password".

### What keeps working

**The screens.** They keep playing exactly what they had, schedules and campaigns included,
because they talk to the server with their own key and never pass through this check. A wrong
date therefore never blanks a venue, and renewing needs nothing done on the screens. Stopping
the screens themselves on expiry would be a separate, deliberate change to the player.

### How people find out

- **In the CMS**, an amber notice at the top of every page starts 14 days before the end. It
  turns red once the account has expired, and says what still works. Settings, Plan & limits
  shows the date too.
- **In the monitoring app**, the account list has an **Active until** column. Accounts carry an
  **Ends in N days** badge in their last 14 days and an **Expired** badge after, so staff can
  follow up.

There is no email, as with everything else here.

The check lives in `_refuse_if_expired` in `backend/app/api/deps.py`. The short list of changes
an expired account may still make, `EXPIRED_MAY_STILL`, sits beside it.

## Where the rules live

One table, `MAY_ISSUE` in `backend/app/services/admin.py`, says which kinds each kind of staff
can issue and set limits on. Everything is checked there, in the service, so no route can forget
it. Anything outside the rules answers 403 with a message written for the person who tried.

The monitoring app mirrors the same table in `monitoring/src/hooks/useStaffRights.ts`, but only
to decide what to offer. Hiding a button is a courtesy. The server is the control.

## Setting an account's kind by hand

The monitoring app issues admin and client accounts itself, so this is only needed for the two
things no API does on purpose: making **the** owner account, and taking staff access away.

```bash
.venv/bin/python -m scripts.set_account_kind --username you --kind owner
```

```bash
.venv/bin/python -m scripts.set_account_kind --username tech --kind client
```

Name anyone in the account and the whole account changes. Making an account the owner clears any
limits it had, and is refused if another owner account already exists. To move the owner, make
the current one admin or client first.

In production this runs inside the backend container. See the Railway notes in
[DEPLOY.md](DEPLOY.md).

## Deleting an account

Also by hand, and also with no API behind it: deleting is not undoable, and it is not something a
customer or a technician should be able to do. It prints what would go and changes nothing until
you add `--yes`.

```bash
.venv/bin/python -m scripts.delete_account --username someone
```

```bash
.venv/bin/python -m scripts.delete_account --username someone --yes
```

It takes the account's people, screens, media, playlists, campaigns, schedules and reviews with
it. The owner account is refused outright. The admin action log keeps its record of the account,
name and all, because a history that vanishes with the thing it describes is no history.

Order matters inside it, which is the reason this is a script rather than one delete statement. A
scene pointing at a file holds that file back on purpose, so that deleting a file still on air is
refused rather than silently punching a hole in a running screen. Playlists therefore go first,
then everything else follows the account.

The files themselves stay in R2. Reclaim them afterwards:

```bash
.venv/bin/python -m scripts.sweep_orphans --delete
```

## Checking it still works

```bash
cd backend && .venv/bin/python -m scripts.check_admin
```

That drives the real HTTP routes: who gets in, who can issue which kind, whose limits each kind
of staff can change, that the owner account refuses limits, that no customer route can change an
account's kind, that the screen limit still bites when pairing, and that an expired account is
read-only while its screens carry on.
