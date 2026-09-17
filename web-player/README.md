# Fortu Player — Web

The browser half of Fortu CMS, for screens that can open a web page but can't install an APK:
smart TVs (Samsung Tizen, LG webOS), a Chromebox or mini PC in kiosk mode, anything with a
modern-ish browser.

It behaves like the Android player (`player/`) on purpose — the engine in `src/engine.ts` is a
port of `PlayerEngine.kt`, and the tests in `test/` mirror `PlayerEngineTest.kt`,
`PlayerPowerTest.kt` and `PowerPlanTest.kt` case for case:

- **Pairing**: open the page, a 6-character code appears, type it into **Devices → Add screen**.
  The screen is recorded in the CMS like any other, marked **Player: Web browser**.
- **Playback**: the same slots, layout, fit, rotation, video advance rules and proof-of-play.
- **Power**: the same weekly schedule and "Turn on/off now" rules, evaluated on the screen's own
  clock. Off means a black screen with nothing decoding and the wake lock released.
- **Settings**: rotation, volume and the touchscreen lock. (The app-lock PIN is hidden for web
  screens — there's no app to exit.)
- **Offline**: pictures are cached in the browser and the player itself by a service worker, so
  a screen that loses its network keeps showing its pictures. **Videos always play from R2** and
  need the network — see the table below.

## Where it differs, and why

| | Android | Web |
|---|---|---|
| Push | MQTT, changes land in ~1s | A browser can't reach the broker's TLS port. Polls every **10s** instead of 30s. |
| Updates | Installs a new APK from a rollout | Reloads itself when a new deploy of this service is live (checked every 5 min, or **Check for update** in the debug overlay). Software rollouts don't apply to web screens. |
| Power off | `lockNow()` (Device Owner only) | Black screen, playback stopped, wake lock released. A browser can't switch off the panel itself. |
| Rotation | `requestedOrientation` | The page draws itself turned 90° when the setting doesn't match the panel's shape. |
| Brightness | Not offered by the CMS yet | Not possible from a browser. |
| Websites | WebView | `<iframe>` — sites that forbid being framed (`X-Frame-Options`) won't show. |
| Video files | Downloaded and played offline | Played straight from R2, never downloaded. TV browsers hand video to the TV's own player, which can open an address but not a file stored inside the browser — cached videos were a black screen on a Samsung Tizen TV. Without network, video slides are skipped and pictures keep looping. |
| Sound | Always | Browsers block autoplay with sound until someone interacts; the player falls back to muted and reports it. Enable autoplay in the TV browser's settings. |

## Setting up a screen

1. Open the web player's URL in the TV's browser.
2. Enter the code in the CMS.
3. Make it stay there: set the page as the browser's home/start page, turn on the browser's
   kiosk or full-screen mode if it has one, and turn off the TV's own screensaver/eco sleep. On
   Chrome: `chrome --kiosk --autoplay-policy=no-user-gesture-required https://<player-url>`.

**Hiding the browser bar**: no web page can go full screen by itself — every browser requires a
key press or tap first. So the player asks on its pairing, idle and error screens ("Press OK on
the remote to hide the browser bar"), and goes full screen on the first press of any remote key.
It then **stays** full screen across automatic updates: the page a screen opens (`index.html`,
`src/shell.ts`) only holds a frame, and updates reload the player inside that frame, never the
page that owns full screen. What still brings the bar back is the TV closing or reloading the
browser itself (a reboot, the browser being closed) — then it's one press again. To never see it,
use the TV's kiosk/URL-launcher mode, or install the page as an app where the browser offers
"Add to home screen" (it opens with no bar, via `manifest.webmanifest`). The debug overlay's
**full screen** row says whether this browser supports it at all.

**Debug overlay**: hold the top-left corner, or press **Menu**, **Info** or **D**. It shows the
server, content version, cache, wake lock and last error, with **Check for update** and
**Reload player**. (A corner hold on top of a website element doesn't reach the page — use a key.)

### Offline pictures need R2 CORS

Picture downloads go straight from the browser to R2, so the bucket's CORS policy must allow the
web player's origin (R2 → `fortu-cms` → Settings → CORS Policy — add it to `AllowedOrigins`, with
`GET`). Without it pictures stream from R2 like videos: everything still plays, but nothing
survives the network dropping. Videos don't need CORS — they're never downloaded.

## Development

```bash
npm install
npm test              # engine + power rules
npm run dev           # http://localhost:5174, proxies /api to the backend on :8001
npm run build && BACKEND_URL=http://localhost:8001 node server.mjs   # production server, :4174
```

`server.mjs` serves `dist/`, proxies `/api/*` to `BACKEND_URL` (same pattern as `frontend/`, so
no CORS setup is needed on the backend), and answers `/version.json` with the running deploy's id,
which is how screens notice a new deploy.
