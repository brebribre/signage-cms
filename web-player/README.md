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
- **Offline**: files are cached in the browser and the player itself is cached by a service
  worker, so a screen that reboots with no network plays its last content.

## Where it differs, and why

| | Android | Web |
|---|---|---|
| Push | MQTT, changes land in ~1s | A browser can't reach the broker's TLS port. Polls every **10s** instead of 30s. |
| Updates | Installs a new APK from a rollout | Reloads itself when a new deploy of this service is live (checked every 5 min, or **Check for update** in the debug overlay). Software rollouts don't apply to web screens. |
| Power off | `lockNow()` (Device Owner only) | Black screen, playback stopped, wake lock released. A browser can't switch off the panel itself. |
| Rotation | `requestedOrientation` | The page draws itself turned 90° when the setting doesn't match the panel's shape. |
| Brightness | Not offered by the CMS yet | Not possible from a browser. |
| Websites | WebView | `<iframe>` — sites that forbid being framed (`X-Frame-Options`) won't show. |
| Sound | Always | Browsers block autoplay with sound until someone interacts; the player falls back to muted and reports it. Enable autoplay in the TV browser's settings. |

## Setting up a screen

1. Open the web player's URL in the TV's browser.
2. Enter the code in the CMS.
3. Make it stay there: set the page as the browser's home/start page, turn on the browser's
   kiosk or full-screen mode if it has one, and turn off the TV's own screensaver/eco sleep. On
   Chrome: `chrome --kiosk --autoplay-policy=no-user-gesture-required https://<player-url>`.

**Debug overlay**: hold the top-left corner, or press **Menu**, **Info** or **D**. It shows the
server, content version, cache, wake lock and last error, with **Check for update** and
**Reload player**. (A corner hold on top of a website element doesn't reach the page — use a key.)

### Offline caching needs R2 CORS

Downloads go straight from the browser to R2, so the bucket's CORS policy must allow the web
player's origin (R2 → `fortu-cms` → Settings → CORS Policy — add it to `AllowedOrigins`, with
`GET`). Without it the player still plays everything, streaming each file from its URL — it just
can't keep playing if the network drops. The debug overlay's **last error** says so.

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
