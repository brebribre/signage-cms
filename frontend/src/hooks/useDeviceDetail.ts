import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import type { DeviceRead, DeviceUpdateBody, PairStartResponse } from '@/types/api'

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
  /** Set once unpair succeeds — the modal shows this instead of closing, since the whole
   *  point is to read the new code off the screen (or off here, until it re-displays it). */
  const freshPairing = ref<PairStartResponse | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      device.value = await api.get(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this screen'
    } finally {
      isLoading.value = false
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

  async function unpair(): Promise<boolean> {
    isSaving.value = true
    saveError.value = null
    try {
      freshPairing.value = await api.unpair(id)
      await refresh()
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not unpair'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function remove(): Promise<boolean> {
    try {
      await api.remove(id)
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not delete'
      return false
    }
  }

  onMounted(refresh)

  return {
    device, isLoading, isSaving, error, saveError, saveSucceeded, freshPairing,
    refresh, save, unpair, remove,
  }
}
