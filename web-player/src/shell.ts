/**
 * The page a screen actually opens: nothing but a full-window frame holding the player
 * (player.html → src/main.ts).
 *
 * It exists for full screen. A browser only goes full screen after someone presses a key or
 * taps, and it leaves full screen whenever the page reloads. The player reloads itself onto every
 * new deploy — so if it were the top page, every update would bring the browser bar back on a
 * screen nobody is standing at. Holding full screen out here means only the frame inside
 * reloads, and full screen survives. The player reaches this page's document directly (same
 * origin) to request it; see "Full screen" in main.ts.
 *
 * Kept deliberately tiny, because this page itself only changes when the TV's browser reloads it.
 */

const frame = document.createElement('iframe')
frame.src = '/player.html'
// What the player needs from inside a frame: video with sound, the screen wake lock, and full
// screen for websites it shows.
frame.allow = 'autoplay; fullscreen; screen-wake-lock; encrypted-media'
document.body.appendChild(frame)

/** Remote keys go to whichever document has focus; the player needs it, not this page. */
const focusPlayer = () => frame.contentWindow?.focus()
frame.addEventListener('load', focusPlayer)
window.addEventListener('focus', focusPlayer)

/** A press that lands out here before the player has loaded still counts. */
function requestFullscreen() {
  const root = document.documentElement as HTMLElement & { webkitRequestFullscreen?: () => void }
  const doc = document as Document & { webkitFullscreenElement?: Element }
  if (document.fullscreenElement || doc.webkitFullscreenElement) return
  try {
    if (root.requestFullscreen) root.requestFullscreen().catch(() => {})
    else root.webkitRequestFullscreen?.()
  } catch {
    /* refused; the player's own hint handles saying so */
  }
  focusPlayer()
}
window.addEventListener('keydown', requestFullscreen, true)
window.addEventListener('pointerdown', requestFullscreen, true)

if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}
