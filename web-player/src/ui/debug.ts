import type { DebugInfo } from '../engine'

/**
 * The diagnostics overlay — the Android player's `DebugOverlay`. Opened by holding the top-left
 * corner, or with Menu / Info / "D" on a remote or keyboard. Buttons are real <button>s, so a TV
 * remote's arrows and OK reach them.
 */

export interface DebugActions {
  onCheckUpdate: () => void
  onReload: () => void
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

function ago(millis: number | null): string {
  if (millis === null) return 'never'
  const seconds = Math.max(0, Math.round((Date.now() - millis) / 1000))
  return seconds < 5 ? 'just now' : seconds < 120 ? `${seconds}s ago` : `${Math.round(seconds / 60)} min ago`
}

export function renderDebug(el: HTMLElement, info: DebugInfo, extra: Record<string, string>, actions: DebugActions) {
  const rows: Array<[string, string]> = [
    ['device', info.deviceName ?? '—'],
    ['api', info.apiHost],
    ['version', info.version?.slice(0, 24) ?? '—'],
    ['items', String(info.itemCount)],
    ['cached', `${(info.cachedBytes / 1_048_576).toFixed(1)} MB`],
    ['dropped frames', String(info.droppedFrames)],
    ['download', info.downloadBytesPerSecond ? `${(info.downloadBytesPerSecond / 1_048_576).toFixed(1)} MB/s` : 'not measured'],
    ['storage', info.storage],
    ['last poll', ago(info.lastPollAt)],
    ['schedule', info.schedule || 'default playlist'],
    ...Object.entries(extra),
    ['update', info.updateStatus ?? 'not checked'],
    ['last error', info.lastError ? `${info.lastError} (${ago(info.lastErrorAt)})` : 'none'],
  ]
  const focused = document.activeElement?.id
  el.innerHTML = `<div>
    <dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
    <button id="dbg-update" type="button">Check for update</button>
    <button id="dbg-reload" type="button">Reload player</button>
    <div class="hint">Hold the top-left corner again, or press Menu, to dismiss</div>
  </div>`
  el.querySelector<HTMLButtonElement>('#dbg-update')!.onclick = actions.onCheckUpdate
  el.querySelector<HTMLButtonElement>('#dbg-reload')!.onclick = actions.onReload
  // Re-rendering must not throw a remote's focus back to nothing mid-navigation.
  el.querySelector<HTMLButtonElement>(`#${focused === 'dbg-reload' ? 'dbg-reload' : 'dbg-update'}`)!.focus()
}
