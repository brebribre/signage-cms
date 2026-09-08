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

### 3. Pair it

Launch the app. It shows a 6-character code. In the CMS: **Devices → Add screen**, type the
code, give it a name and location. The screen picks up its token within ~5 seconds and moves to
the idle card. Assign a playlist and it starts playing within 30 seconds.

The code is deliberately drawn from an unambiguous alphabet — no `O`/`0`, no `I`/`1`/`L` —
because it gets read off a television from across a room.

---

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
and unlocks silent APK updates later. Requires a **factory-reset device with no Google account
added**:

```bash
adb shell dpm set-device-owner com.fortu.player/.DeviceAdminReceiver
```

This app does not ship a `DeviceAdminReceiver` yet — Device Owner is Phase 12c. Options 1 and 2
are available today.

---

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
