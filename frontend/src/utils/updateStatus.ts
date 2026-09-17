import type { DeviceRead } from '@/types/api'

/**
 * One screen's software update, as something a person can read — derived from the pin the CMS
 * set and whatever the screen has reported since. Pure, so the Screens page, the screen's own
 * page and the Software updates list all tell the same story.
 *
 * The states are the ones every device-management product ends up with (queued → downloading →
 * installing → done / failed), plus the two that only exist from the CMS's side of the wire:
 * "pending" — offered, nothing heard yet — and "stalled" — the screen was mid-update and has
 * gone quiet. Before this the page said "Update pending" for all of them.
 */

export type UpdateKind = 'pending' | 'downloading' | 'installing' | 'stalled' | 'installed' | 'failed'

export interface UpdateView {
  kind: UpdateKind
  version: string
  /** One line: what is happening. */
  title: string
  /** One or two sentences: why, and what (if anything) to do about it. */
  detail: string
  /** 0–100 while downloading and the screen has said how far it is. */
  percent: number | null
  /** Something is (or should be) happening right now — show the spinner, keep polling. */
  busy: boolean
  tone: 'neutral' | 'danger' | 'success'
  /** "Cancel" while waiting, "Dismiss" once it has finished either way. */
  canCancel: boolean
  canRetry: boolean
}

/** A "downloading"/"installing" report older than this is treated as the screen having gone
 *  quiet. The player reports at least every few seconds while it is still working — mirrors
 *  backend/app/services/device_sync.py's UPDATE_REPORT_STALE_SECONDS. */
export const UPDATE_REPORT_STALE_MS = 180_000
/** How long a pinned update can sit unacknowledged by an online screen before it's worth
 *  saying the screen probably can't take it. */
const PENDING_TOO_LONG_MS = 180_000
/** Matches StatusDot's "live" threshold. */
const ONLINE_MS = 120_000

/** The screen's reasons arrive without a full stop; one is needed before the next sentence. */
function sentence(text: string): string {
  return /[.!?…]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`
}

function minutes(ms: number): string {
  const m = Math.max(1, Math.round(ms / 60_000))
  return `${m} min`
}

function seconds(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  return s < 60 ? `${s}s` : minutes(ms)
}

export function describeUpdate(d: DeviceRead, now: number = Date.now()): UpdateView | null {
  const pin = d.forced_update_version
  const reportedAt = d.update_reported_at ? new Date(d.update_reported_at).getTime() : null
  const reportAge = reportedAt === null ? null : now - reportedAt
  const seenAge = d.last_seen_at ? now - new Date(d.last_seen_at).getTime() : null
  const online = seenAge !== null && seenAge < ONLINE_MS

  // A report counts when it's about the pinned build, or when there's no pin at all (a fleet
  // rollout produces the same reports). A report about some other version is about an earlier
  // attempt — the pin is the newer instruction, and it hasn't been heard yet.
  const report =
    d.update_state && d.update_version && reportAge !== null && (!pin || d.update_version === pin)
      ? { state: d.update_state, version: d.update_version, age: reportAge }
      : null

  if (report) {
    const { state, version, age } = report
    if (state === 'downloading' || state === 'installing') {
      if (age > UPDATE_REPORT_STALE_MS) {
        return {
          kind: 'stalled',
          version,
          title: `No news from the screen for ${minutes(age)}`,
          detail:
            state === 'downloading'
              ? `It was downloading ${version}${d.update_progress_pct !== null ? ` (${d.update_progress_pct}%)` : ''} and has gone quiet — most likely it lost its connection. It keeps trying by itself and picks the download up where it left off.`
              : `It started installing ${version} and hasn't checked in since. The player normally restarts itself within a minute; if it doesn't come back, power-cycle the screen.`,
          percent: state === 'downloading' ? d.update_progress_pct : null,
          busy: true,
          tone: 'neutral',
          canCancel: true,
          canRetry: false,
        }
      }
      if (state === 'downloading') {
        return {
          kind: 'downloading',
          version,
          title: `Downloading ${version}`,
          detail: `${d.update_progress_pct !== null ? `${d.update_progress_pct}% · ` : ''}last report ${seconds(age)} ago`,
          percent: d.update_progress_pct,
          busy: true,
          tone: 'neutral',
          canCancel: true,
          canRetry: false,
        }
      }
      return {
        kind: 'installing',
        version,
        title: `Installing ${version}`,
        detail: 'The player restarts itself when it’s done — usually under a minute. This page confirms once the screen checks in on the new build.',
        percent: null,
        busy: true,
        tone: 'neutral',
        canCancel: true,
        canRetry: false,
      }
    }
    if (state === 'failed') {
      return {
        kind: 'failed',
        version,
        title: `Update to ${version} failed`,
        detail:
          sentence(d.update_detail || 'The screen gave no reason') +
          (pin ? ' The screen retries by itself in about 10 minutes, or retry it now.' : ''),
        percent: null,
        busy: false,
        tone: 'danger',
        canCancel: true,
        canRetry: true,
      }
    }
    // installed
    return {
      kind: 'installed',
      version,
      title: `Updated to ${version}`,
      detail: `The screen checked in running it ${seconds(age)} ago.`,
      percent: null,
      busy: false,
      tone: 'success',
      canCancel: true,
      canRetry: false,
    }
  }

  if (pin) {
    const at = d.forced_update_at ? new Date(d.forced_update_at).getTime() : null
    if (at !== null && at > now) {
      return {
        kind: 'pending',
        version: pin,
        title: `${pin} scheduled`,
        detail: `Starts at ${new Date(at).toLocaleString()} on the screen’s next check-in after that.`,
        percent: null,
        busy: false,
        tone: 'neutral',
        canCancel: true,
        canRetry: false,
      }
    }
    const waited = at !== null ? now - at : 0
    let detail: string
    if (!online) {
      detail = `The screen hasn’t checked in for ${seenAge === null ? 'a while' : minutes(seenAge)} — it’s offline or asleep. The download starts as soon as it reconnects.`
    } else if (waited > PENDING_TOO_LONG_MS) {
      detail = `The screen is checking in but hasn’t started after ${minutes(waited)}. It may be running a player too old to report progress, or it isn’t provisioned as Device Owner and can’t install updates by itself.`
    } else {
      detail = 'The screen checks in every 30 seconds; the download starts on the next one.'
    }
    return {
      kind: 'pending',
      version: pin,
      title: 'Waiting for the screen to check in',
      detail,
      percent: null,
      busy: true,
      tone: 'neutral',
      canCancel: true,
      canRetry: false,
    }
  }

  return null
}
