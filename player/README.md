# Fortu Player — Android

The screen half of Fortu CMS. Pairs itself to an account, pulls its playlist, caches every
file to local disk, and plays the loop — continuing to play with the network unplugged.

Built against the Phase 10 device-sync API: `GET /device/manifest` and `POST /device/heartbeat`,
authenticated with a device token (never a user session).

---

## Quickest path: run it on an emulator first

You do not need hardware to see this working end to end.

**With Android Studio** (easiest if you have it, or don't mind a ~1 GB install):

1. Install [Android Studio](https://developer.android.com/studio).
2. **Open** this `player/` folder (File → Open — not "Import project"). Gradle syncs on its own.
3. Tools → Device Manager → **Add a virtual device**. Any phone or tablet profile works;
   a **tablet in landscape** looks closest to a real signage screen.
4. Press **Run ▶**. The app launches showing a 6-character pairing code.
5. In the CMS → **Devices → Add screen**, type that code. The emulator switches to the idle
   card within ~5 seconds, then starts playing once you assign a playlist.

**From the command line** (no Android Studio — this repo is already set up for it):

```bash
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools   # macOS/Homebrew
cd player
./gradlew assembleDebug                    # produces app/build/outputs/apk/debug/app-debug.apk
$ANDROID_HOME/emulator/emulator -avd fortu-test -no-snapshot &
$ANDROID_HOME/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk
$ANDROID_HOME/platform-tools/adb shell am start -n com.fortu.player.debug/com.fortu.player.MainActivity
```

Create the AVD once, first:

```bash
sdkmanager --install "emulator" "system-images;android-35;google_apis;arm64-v8a"
avdmanager create avd -n fortu-test -k "system-images;android-35;google_apis;arm64-v8a" -d "10.1in WXGA (Tablet)"
```

### Emulator caveat worth knowing

The emulator talks to a **cloud** API here, so it just works. If you ever point the app at a
backend running on *your own machine*, `localhost` inside the emulator means the emulator
itself — use `10.0.2.2`, which is how the emulator reaches your host:

```bash
./gradlew assembleDebug -PapiBaseUrl=http://10.0.2.2:8001
```

---

## Deploying to a real screen

### 1. Build the APK

```bash
cd player
./gradlew assembleRelease
# → app/build/outputs/apk/release/app-release.apk
```

It's signed with the debug key, so it installs by sideloading with no keystore setup. That is
fine for screens you own and sideload yourself; a Play Store listing would need a real signing
config.

To point a build at a different backend:

```bash
./gradlew assembleRelease -PapiBaseUrl=https://your-api.example.com
```

**The API URL is compiled in, not configured on the device.** A screen with no keyboard cannot
be asked to type one. This is also why the plan says to settle a custom domain *before* pairing
real hardware — changing it later means rebuilding and reinstalling on every screen.

### 2. Get it onto the device

**Over USB** (simplest):

1. On the device: Settings → About → tap **Build number** 7 times to unlock Developer options.
2. Settings → Developer options → enable **USB debugging**.
3. Plug it into your computer, accept the "Allow USB debugging?" prompt on the device.
4. ```bash
   adb install -r app/build/outputs/apk/release/app-release.apk
   ```

**Without a cable** — put the APK on a USB stick or in cloud storage, open it with the device's
file manager, and allow "install from unknown sources" when prompted.

**Over the network**, if the device is on your wifi and has wireless debugging (Android 11+):

```bash
adb pair <device-ip>:<pairing-port>     # code shown under Developer options → Wireless debugging
adb connect <device-ip>:5555
adb install -r app/build/outputs/apk/release/app-release.apk
```

### What the screen shows while pairing

The pairing screen displays the code, a **pulsing indicator with a poll counter**, and — most
usefully — **the server it is talking to**. Pairing "not working" is almost always the screen and
the CMS being pointed at different backends, and that host line is the only way to see it without
a laptop.

After a human claims it, the screen shows **Connected** briefly, then **Preparing content** with
real download progress before the first frame. A large video over venue wifi takes long enough
that a blank screen reads as broken.

### 3. Pair it

Launch the app. It shows a 6-character code. In the CMS: **Devices → Add screen**, type the
code, give it a name and location. The screen picks up its token within ~5 seconds and moves to
the idle card. Assign a playlist and it starts playing within 30 seconds.

The code is deliberately drawn from an unambiguous alphabet — no `O`/`0`, no `I`/`1`/`L` —
because it gets read off a television from across a room.

---

## Orientation

**Set per screen in the CMS, applied by the app at runtime** — the activity deliberately has no
`screenOrientation` in its manifest. One APK therefore serves portrait totems and landscape
panels without a separate build for each.

New devices default to **portrait**, since tall totems are the common case here. Change it on the
device's page in the CMS; the screen picks it up on its next poll (within 30s) with no reinstall.

While a screen is still pairing it uses whatever the hardware reports, rather than guessing — a
pairing code is legible either way, and forcing a guess would make the screen visibly flip once
the real value arrives.

## Making it a real kiosk

The app already keeps the screen awake, hides the system bars, locks to landscape, and
relaunches after a power cut. What it does *not* do by default is stop someone pressing Home.
Three options, weakest to strongest:

**1. Screen pinning** — works on any device, no setup. Settings → Security → App pinning, then
pin the app from the recents screen. Dismissible with a button combination, so it stops
accidents rather than determined people.

**2. Make the app the launcher** — the screen boots straight into the player and Home returns to
it. Uncomment the `HOME`/`DEFAULT` intent-filter block in
[`app/src/main/AndroidManifest.xml`](app/src/main/AndroidManifest.xml), rebuild, install, then
pick Fortu Player when Android asks which launcher to use.

> Don't do this on your personal phone — it will ask to become your launcher. It is meant for
> hardware dedicated to signage.

**3. Device Owner mode** — the real answer for screens you control. Genuinely cannot be exited,
disables the lock screen and system-update prompts, and unlocks silent APK updates. See the
provisioning runbook below.

---

## Provisioning runbook (Device Owner)

Ten minutes per screen, once. **The device must be factory-reset with no Google account added**
— Android refuses to grant Device Owner otherwise, and there is no way around it short of
resetting again. This is why it's a provisioning step rather than a setting you can flip later.

1. **Factory reset** the device. Settings → System → Reset → Erase all data.
2. Walk through setup and **skip the Google account step**. Skip wifi too if it offers, then add
   wifi from Settings afterwards — some setup wizards silently add an account when online.
3. Enable **Developer options** (Settings → About → tap Build number ×7) and **USB debugging**.
4. Install and grant ownership:
   ```bash
   adb install -r app/build/outputs/apk/release/app-release.apk
   adb shell dpm set-device-owner com.fortu.player/com.fortu.player.kiosk.DeviceAdminReceiver
   ```
   Expect `Success: Device owner set to package com.fortu.player`. If it fails with
   *"Not allowed to set the device owner because there are already some accounts on the
   device"*, an account slipped in during setup — factory reset and redo step 2.
5. **Launch the app.** It applies the full policy on first run: lock task mode, no lock screen,
   stay-on-while-plugged, deferred system updates, and itself as the persistent launcher.
6. **Pair it** — read the code off the screen, enter it in the CMS.
7. **Verify:** long-press for the debug overlay. The `kiosk` row should read
   **`device owner (full kiosk)`**. If it says `not owner (screen pinning only)`, step 4 didn't
   take.
8. Reboot the device once and confirm it comes back into the loop on its own.

### Undoing it

Device Owner cannot be removed with `adb` once set. Either factory reset the device, or add a
temporary removal path in the app calling `dpm.clearDeviceOwnerApp()`. Worth knowing **before**
you provision a device you might need back for something else.

### What the policy actually changes

| Setting | Effect |
|---|---|
| `setLockTaskPackages` + `startLockTask` | Only this app can hold the foreground. Home and Recents do nothing. |
| `setKeyguardDisabled` | No lock screen to get stuck behind after a reboot. |
| `STAY_ON_WHILE_PLUGGED_IN` | Screen never sleeps while powered — signage is always plugged in. |
| `setSystemUpdatePolicy` (windowed) | System updates install between 03:00–05:00 instead of covering the screen mid-day. |
| `addPersistentPreferredActivity` | The player *is* the launcher, so boot lands in the loop. |

**All of it degrades safely.** On a device that isn't Device Owner — your phone, an emulator, a
sideloaded install — every one of those calls is skipped and the app falls back to screen
pinning. The same APK is safe everywhere, which is why the `HOME` intent-filter in the manifest
stays commented out: the policy grants launcher status only where ownership was actually
granted.

---

## Silent updates

Once a screen is Device Owner, `SelfUpdater` can download an APK and install it over itself with
no prompt and no visit. That is the feature that decides whether a fleet of screens is
maintainable or a recurring field trip.

### Releasing a new version

1. Bump `versionName` in [`app/build.gradle.kts`](app/build.gradle.kts).
2. Build it:
   ```bash
   ./gradlew assembleRelease
   ```
3. Upload to R2 — the script reads the version straight out of the APK, so the published
   version can never disagree with what the binary reports:
   ```bash
   cd ../backend
   .venv/bin/python -m scripts.publish_player_apk \
     ../player/app/build/outputs/apk/release/app-release.apk
   ```
4. It uploads, verifies, and prints the two variables to set. **Uploading does not publish** —
   setting these does, and it pushes an install to every screen at once, so it stays a
   deliberate act:
   ```bash
   railway variables --service signage-cms \
     --set 'PLAYER_LATEST_VERSION=1.1.0' \
     --set 'PLAYER_APK_KEY=apks/fortu-player-1.1.0.apk'
   ```

Screens pick it up on their next heartbeat (~30 s) and install silently. **Rolling back is the
same command** pointing at an earlier version already in R2 — updates are offered whenever a
screen's version *differs* from the published one, not only when it's older. That's deliberate:
if a release breaks playback across a wall of screens, the fix has to be a config change rather
than a visit to each one.

### What protects you from a bad push

- **Blank config publishes nothing.** `PLAYER_LATEST_VERSION` is empty by default, so a
  misconfiguration cannot accidentally roll out an APK.
- **Version is read from the APK**, not typed. A mismatch between the published string and the
  binary's real `versionName` would make every screen reinstall on every heartbeat forever;
  `publish_player_apk.py` refuses to guess and errors out instead.
- **One install attempt per app run.** A failing install is not retried until the app restarts,
  so a bad APK cannot become a 30-second re-download loop.
- **A screen that has never reported its version is offered nothing** — pushing blind risks
  exactly that loop.
- **Non-owner devices decline.** `SelfUpdater.downloadAndInstall()` refuses to run rather than
  falling back to the normal installer: that path shows a confirmation dialog nobody is standing
  in front of, parking a screen on a permission prompt instead of playing — strictly worse than
  not updating. Sideloaded and development installs update with `adb install -r` as usual.

---

## Auto-start after a power cut

**A plain install does not relaunch itself on boot, and cannot.** Since Android 10 an app may
not start an activity from the background, so a boot receiver calling `startActivity()` is
silently discarded — the device comes back to its normal launcher. That is correct behaviour, not
a fault: an app that could force itself to the foreground on any phone would be malware.

Two configurations make it legal, and a real signage deployment wants one of them regardless:

- **Device Owner** (see the provisioning runbook above). `KioskPolicy` registers the app as the
  persistent preferred HOME activity, so the system launches it on boot with no receiver
  involved.
- **Declare the app as the launcher** — uncomment the `HOME` intent-filter in
  `AndroidManifest.xml` and rebuild. Same result, no factory reset needed, but do not do it on a
  device you use for anything else.

While testing on an emulator or your own phone, just tap the app icon after a boot.

## Tests

```bash
./gradlew testDebugUnitTest
```

Twenty tests over `PlayerEngine`, the state machine, on a plain JVM — no device, no emulator,
under a second to run.

They exist because **five real bugs reached hardware before this app had a single test**: a blur
handler that never fired, orientation the player ignored entirely, a boot receiver that could not
work on Android 10+, a screen that hung on the splash forever, and a single 401 permanently
unpairing a working screen. Four of the five were state-machine behaviour, and every one passed a
fully green backend suite — because a server-side test cannot see the client discarding a value.

The engine takes its collaborators as interfaces (`PlayerApi`, `TokenStore`, `MediaStore`) and its
dispatcher as a parameter, purely so this is possible. Before that refactor the ViewModel built
its own `ApiClient`, `DeviceStore` and `MediaCache`, and the loop could only be tested by
installing the app and watching it.

What they pin down, each mapping to something that actually broke or could:

- an unpaired screen shows a code, names its server, and visibly keeps polling
- an expired code is replaced rather than displayed forever
- **a paired screen that cannot sync shows `Trouble`, never hangs on the splash**
- **trouble never replaces content that is already playing** — a failed poll must not blank a wall
- **one 401 does not unpair a screen; repeated 401s still do**, so a real revocation works
- content downloads before it is shown, and eviction happens only afterwards
- one bad file does not stop the rest of the loop
- **orientation from the manifest reaches the state the UI reads**
- a 304 changes nothing and re-downloads nothing
- plays batch onto the next heartbeat and are drained, not resent forever
- an update is never attempted where it cannot install silently, and a failed one is not retried

Verified by mutation: reintroducing the single-401 wipe or dropping orientation from the state
each fails three tests.

## Diagnosing a screen in front of you

**Long-press anywhere** to toggle a debug overlay: device name, API URL, manifest version,
cached size, item count, last poll and last error. There is no keyboard on a signage screen and
no way to read logcat from across a lobby, so this is the diagnostic surface.

The pairing screen is also the app's error state. An unpaired, revoked, or rejected device
always lands back on a visible code rather than a black screen — **a screen showing a code can
be diagnosed from across the room; a black one cannot.**

If a screen was removed or unpaired in the CMS, its token stops working and it shows a fresh
pairing code on its own. Nothing needs to be done to the hardware.

---

## What it actually does

- **Caches by checksum, never by URL.** The manifest's presigned URLs expire every 6 hours and
  are re-issued on each fetch; keying the cache on URL would re-download the whole playlist
  several times a day. The checksum is the content's identity and never changes.
- **Plays from local disk, always.** Never streams from the presigned URL. Venue wifi dropping
  should have no visible effect at all — that is the entire point of the cache.
- **Downloads before switching, evicts after.** A screen never shows a gap while a file is
  still arriving, and never ends up with a half-empty cache if the network dies mid-swap.
- **Polls with an ETag.** Nothing changed is a `304` costing a few hundred bytes, which is the
  normal case on almost every 30-second poll.
- **Survives a bad file.** One item failing to download doesn't stop the rest of the loop
  updating; the player skips anything still missing.

## Stack

| Concern | Choice |
|---|---|
| Language / UI | Kotlin + Jetpack Compose |
| Video | Media3 (ExoPlayer) — hardware decoder selection, correct scaling modes |
| Images | Coil |
| HTTP | OkHttp + kotlinx.serialization |
| Token storage | DataStore, unencrypted — see below |
| minSdk | 24 (Android 7), targetSdk 35 |

The device token is stored unencrypted on purpose. It is a bearer credential on hardware you
physically control: `androidx.security-crypto` is deprecated, anyone with root and the device in
hand wins anyway, and the controls that actually matter are Device Owner mode plus
`POST /devices/{id}/unpair`, which revokes it centrally. Encrypting it locally would be theatre.
