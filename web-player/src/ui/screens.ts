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
      return `<div class="screen"><div class="brand">FORTU</div></div>`

    case 'pairing':
      return `<div class="screen"><div class="col">
        <div class="brand">FORTU</div>
        <div class="muted" style="font-size:4vmin;margin-top:7vmin">Enter this code in the CMS</div>
        <div class="code">${esc(s.code)}</div>
        <div class="row muted" style="font-size:3vmin;margin-top:4vmin">
          <span class="dot"></span>
          <span>${s.checks === 0 ? 'Waiting for the CMS' : `Waiting for the CMS · checked ${s.checks}×`}</span>
        </div>
        <div class="subtle" style="font-size:2.6vmin;margin-top:5vmin">${esc(s.apiHost)}</div>
        ${s.error ? `<div class="muted" style="font-size:3vmin;margin-top:2vmin">${esc(s.error)}</div>` : ''}
      </div></div>`

    case 'claimed':
      return `<div class="screen"><div class="col">
        <div style="font-size:8vmin;font-weight:500">Connected</div>
        <div class="muted" style="font-size:4vmin;margin-top:1.8vmin">${esc(s.deviceName)}</div>
      </div></div>`

    case 'preparing': {
      const pct = s.total > 0 ? Math.round((s.done / s.total) * 100) : 0
      return `<div class="screen"><div class="col" style="width:100%">
        <div style="font-size:6vmin;font-weight:500">${esc(s.deviceName)}</div>
        <div class="muted" style="font-size:3.6vmin;margin-top:1.4vmin">Preparing content</div>
        <div class="progress"><div style="width:${pct}%"></div></div>
        <div class="subtle" style="font-size:2.7vmin;margin-top:2.5vmin">${s.done} of ${s.total}${s.currentFile ? ` · ${esc(s.currentFile)}` : ''}</div>
      </div></div>`
    }

    case 'idle':
      return `<div class="screen"><div class="col">
        <div style="font-size:8.5vmin;font-weight:500">${esc(s.deviceName)}</div>
        <div class="muted" style="font-size:4vmin;margin-top:2vmin">No content assigned</div>
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
