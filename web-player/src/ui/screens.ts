import logoUrl from '../assets/paskall-wordmark.png'
import type { PlayerState } from '../engine'

/**
 * Every non-playing state, drawn — the same screens, with the same words, as the Android
 * player's `ui/Screens.kt`. The pairing screen is deliberately the error state too: a screen
 * showing a code can be diagnosed from across a room, a black one cannot.
 */

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)

type StatusState = Exclude<PlayerState, { kind: 'playing' }>

export function statusScreenHtml(s: StatusState): string {
  switch (s.kind) {
    case 'starting':
      return `<div class="screen screen-brand"><img class="logo" src="${logoUrl}" alt="Paskall"></div>`

    // In Paskall's own look — the first thing anyone setting up a screen sees. No server address
    // and no poll count: the code and "waiting" are all a person in front of it needs.
    case 'pairing':
      return `<div class="screen screen-brand"><div class="col">
        <img class="logo" src="${logoUrl}" alt="Paskall">
        <div class="pair-card">
          <div class="pair-label">Enter this code in the CMS</div>
          <div class="code">${esc(s.code)}</div>
        </div>
        <div class="row pair-status">
          <span class="dot"></span>
          <span>Waiting for the CMS</span>
        </div>
        ${s.error ? `<div class="pair-status" style="margin-top:2vmin">${esc(s.error)}</div>` : ''}
      </div></div>`

    case 'claimed':
      return `<div class="screen"><div class="col">
        <div style="font-size:8vmin;font-weight:500">Connected</div>
        <div class="muted" style="font-size:4vmin;margin-top:1.8vmin">${esc(s.deviceName)}</div>
      </div></div>`

    // Downloading before the first frame, in the same look as pairing and idle: one bar for the
    // whole job in bytes, and the speed beside it — a slow bar with a speed is slow wifi, a slow
    // bar without one looks stuck.
    case 'preparing': {
      const pct = s.totalBytes > 0 ? Math.min(100, Math.round((s.doneBytes / s.totalBytes) * 100)) : 0
      const mb = (n: number) => (n / 1_048_576).toFixed(1)
      const amount = `${mb(s.doneBytes)} of ${mb(s.totalBytes)} MB`
      const speed = s.bytesPerSecond ? ` · ${mb(s.bytesPerSecond)} MB/s` : ''
      return `<div class="screen screen-brand"><div class="col">
        <img class="logo" src="${logoUrl}" alt="Paskall">
        <div class="pair-card prep-card">
          <div class="pair-label">Preparing content</div>
          <div class="progress progress-brand${s.totalBytes > 0 ? '' : ' indeterminate'}"><div style="width:${pct}%"></div></div>
          <div class="prep-amount">${esc(amount + speed)}</div>
          ${s.currentFile ? `<div class="prep-file">${esc(s.currentFile)}</div>` : ''}
        </div>
        <div class="row pair-status">
          <span class="dot"></span>
          <span>${esc(s.deviceName)}</span>
        </div>
      </div></div>`
    }

    // Paired, nothing assigned — a valid state, not an error, so it wears the pairing screen's
    // look: the screen's name on the card where the code was, the same pulse to say it's alive.
    case 'idle':
      return `<div class="screen screen-brand"><div class="col">
        <img class="logo" src="${logoUrl}" alt="Paskall">
        <div class="pair-card">
          <div class="pair-label">No content assigned</div>
          <div class="idle-name">${esc(s.deviceName)}</div>
        </div>
        <div class="row pair-status">
          <span class="dot"></span>
          <span>Connected · assign a playlist in the CMS</span>
        </div>
      </div></div>`

    case 'trouble':
      return `<div class="screen"><div class="col">
        <div style="font-size:6vmin;font-weight:500">${esc(s.deviceName ?? 'This screen')}</div>
        <div class="muted" style="font-size:4vmin;margin-top:1.8vmin">Cannot reach the server</div>
        <div class="subtle" style="font-size:2.9vmin;margin-top:4vmin">${esc(s.apiHost)}</div>
        <div class="subtle" style="font-size:2.5vmin;margin-top:1.4vmin">${esc(s.message)}</div>
        <div class="muted" style="font-size:2.7vmin;margin-top:4vmin">Retrying — attempt ${s.attempts}</div>
      </div></div>`
  }
}
