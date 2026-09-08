import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import type { DeviceOrientation, DeviceRead, PairStartResponse } from '@/types/api'

export function useDeviceDetail(id: string) {
  const api = useDeviceApi()

  const device = ref<DeviceRead | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const saveError = ref<string | null>(null)
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

  const rename = (name: string) => run(() => api.update(id, { name }))
  const setLocation = (location: string) => run(() => api.update(id, { location }))
  const setOrientation = (orientation: DeviceOrientation) =>
    run(() => api.update(id, { orientation }))
  const assignPlaylist = (playlistId: string | null) =>
    run(() =>
      api.update(id, playlistId ? { playlist_id: playlistId } : { clear_playlist: true }),
    )

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
    device, isLoading, isSaving, error, saveError, freshPairing,
    refresh, rename, setLocation, setOrientation, assignPlaylist, unpair, remove,
  }
}
