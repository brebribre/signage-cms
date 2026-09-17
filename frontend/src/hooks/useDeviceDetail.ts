import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import type { DeviceRead, DeviceUpdateBody } from '@/types/api'
import { describeUpdate } from '@/utils/updateStatus'

export function useDeviceDetail(id: string) {
  const api = useDeviceApi()

  const device = ref<DeviceRead | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  /** True for a couple of seconds right after a save lands — long enough for the checkmark
   *  to register as "this just happened", not so long it looks stuck. */
  const saveSucceeded = ref(false)

  /** `silent` skips the loading flag — used while polling during a probe, where flashing
   *  the whole page to "Loading…" every couple of seconds would be worse than the thing
   *  it's trying to show. */
  async function refresh(silent = false) {
    if (!silent) isLoading.value = true
    error.value = null
    try {
      device.value = await api.get(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this screen'
    } finally {
      if (!silent) isLoading.value = false
    }
  }

  async function run(fn: () => Promise<DeviceRead>): Promise<boolean> {
    isSaving.value = true
    saveError.value = null
    try {
      device.value = await fn()
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not save'
      return false
    } finally {
      isSaving.value = false
    }
  }

  /**
   * One PATCH for every edited field, sent only when the user explicitly asks — never on a
   * per-field blur or change event.
   *
   * A screen picks up a changed playlist, orientation or timezone within moments, and until
   * now each field firing its own silent PATCH meant a device could be mid-update several
   * times over while someone was still working through the form, with nothing on screen to
   * say so. Batching into one save the user triggers themselves means one moment where the
   * device changes, one loading state, and one confirmation that it took.
   */
  async function save(body: DeviceUpdateBody): Promise<boolean> {
    saveSucceeded.value = false
    const ok = await run(() => api.update(id, body))
    if (ok) {
      saveSucceeded.value = true
      setTimeout(() => { saveSucceeded.value = false }, 2500)
    }
    return ok
  }

  /** Pins this one screen to a specific build, independent of the fleet rollout. Reuses the
   *  same `saveError`/`isSaving` pair as `save` — this is just another kind of change to the
   *  device row, not a separate flow with its own loading state. */
  async function setForcedUpdate(version: string): Promise<boolean> {
    return run(() => api.setForcedUpdate(id, { version }))
  }

  async function cancelForcedUpdate(): Promise<boolean> {
    return run(() => api.cancelForcedUpdate(id))
  }

  /**
   * Disconnecting is a handshake, like pairing was — not a delete the screen finds out about
   * three rejected polls later. The screen is told (it resets itself: back to a pairing code,
   * awake, unlocked, its cached content gone) and the row disappears the moment it has heard;
   * this polls for that. A screen that never answers — offline, asleep for good — is removed
   * anyway after the grace period and re-pairs by itself whenever it next connects.
   */
  const DISCONNECT_TIMEOUT_MS = 20_000
  const DISCONNECT_INTERVAL_MS = 1_000
  const disconnectState = ref<'idle' | 'disconnecting' | 'disconnected' | 'removed' | 'failed'>('idle')

  async function disconnect(): Promise<boolean> {
    disconnectState.value = 'disconnecting'
    saveError.value = null
    try {
      await api.disconnect(id)
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not disconnect this screen'
      disconnectState.value = 'failed'
      return false
    }
    const deadline = Date.now() + DISCONNECT_TIMEOUT_MS
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, DISCONNECT_INTERVAL_MS))
      try {
        await api.get(id)
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          disconnectState.value = 'disconnected'
          return true
        }
        // Anything else is the CMS's own trouble, not the screen's answer — keep waiting.
      }
    }
    // Never heard back. Remove it regardless: the screen finds out by the old route (its token
    // stops working) the next time it connects, and the account isn't left with a ghost.
    try {
      await api.remove(id)
      disconnectState.value = 'removed'
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not remove this screen'
      disconnectState.value = 'failed'
      return false
    }
  }

  /** Nothing can call the device directly — it only ever polls in — so "probe" means: ask it
   *  to check in now, then watch `last_seen_at` for a value newer than the moment asked.
   *  Long enough to cover the device's own ~30s poll cadence even with no push available. */
  const PROBE_TIMEOUT_MS = 40_000
  const PROBE_INTERVAL_MS = 2_000
  const probeState = ref<'idle' | 'probing' | 'online' | 'no-response'>('idle')

  async function probe(): Promise<void> {
    probeState.value = 'probing'
    try {
      const result = await api.probe(id)
      const baseline = new Date(result.probed_at).getTime()
      const deadline = Date.now() + PROBE_TIMEOUT_MS

      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, PROBE_INTERVAL_MS))
        await refresh(true)
        const seenAt = device.value?.last_seen_at
        if (seenAt && new Date(seenAt).getTime() >= baseline) {
          probeState.value = 'online'
          setTimeout(() => { if (probeState.value === 'online') probeState.value = 'idle' }, 4000)
          return
        }
      }
      probeState.value = 'no-response'
    } catch {
      probeState.value = 'no-response'
    }
  }

  /**
   * While a software update is in flight — pinned and unacknowledged, downloading, installing —
   * the page keeps asking, so the percentage moves and a failure shows the moment the screen
   * reports it, rather than whenever someone thinks to reload. Quick at first, when things are
   * expected to move; slower once it's been a while, since a screen still downloading at minute
   * six over bad wifi is not going to change much in two seconds. A finished update (failed,
   * installed, scheduled for later) is still watched, just slowly: a screen retries a failed
   * install by itself after ten minutes, and the page should notice when it does. Stops by
   * itself once there is nothing to show, or the page is left.
   */
  const UPDATE_POLL_FAST_MS = 2_500
  const UPDATE_POLL_SLOW_MS = 10_000
  const UPDATE_POLL_IDLE_MS = 15_000
  const UPDATE_POLL_SLOW_AFTER_MS = 5 * 60_000
  const updateWatch = computed<'off' | 'idle' | 'busy'>(() => {
    const view = device.value ? describeUpdate(device.value) : null
    return view ? (view.busy ? 'busy' : 'idle') : 'off'
  })
  let updatePollTimer: ReturnType<typeof setTimeout> | null = null
  let updatePollStartedAt = 0

  function stopUpdatePoll() {
    if (updatePollTimer !== null) clearTimeout(updatePollTimer)
    updatePollTimer = null
  }

  function scheduleUpdatePoll() {
    stopUpdatePoll()
    const mode = updateWatch.value
    if (mode === 'off') return
    const delay =
      mode === 'idle' ? UPDATE_POLL_IDLE_MS
      : Date.now() - updatePollStartedAt > UPDATE_POLL_SLOW_AFTER_MS ? UPDATE_POLL_SLOW_MS
      : UPDATE_POLL_FAST_MS
    updatePollTimer = setTimeout(async () => {
      await refresh(true)
      scheduleUpdatePoll()
    }, delay)
  }

  watch(
    updateWatch,
    (mode, previous) => {
      if (mode === 'busy' && previous !== 'busy') updatePollStartedAt = Date.now()
      scheduleUpdatePoll()
    },
    { immediate: true },
  )

  onMounted(refresh)
  onUnmounted(stopUpdatePoll)

  return {
    device, isLoading, isSaving, error, saveError, saveSucceeded, probeState, disconnectState,
    refresh, save, disconnect, probe, setForcedUpdate, cancelForcedUpdate,
  }
}
