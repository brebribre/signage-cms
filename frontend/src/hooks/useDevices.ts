import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import type { ClaimBody, DeviceRead, DeviceUpdateBody } from '@/types/api'

/** The screen list: loading, claiming a new one, and the mutations its rows need inline. */
export function useDevices() {
  const api = useDeviceApi()

  const items = ref<DeviceRead[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const claimError = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load screens'
    } finally {
      isLoading.value = false
    }
  }

  /** True on success, so the container knows to close the modal. */
  async function claim(body: ClaimBody): Promise<boolean> {
    isSaving.value = true
    claimError.value = null
    try {
      await api.claim(body)
      await refresh()
      return true
    } catch (e) {
      // 404 already reads as "No screen is waiting with that code…", 429 as
      // "Too many attempts…" — shown as they came rather than replaced with "Error".
      claimError.value = e instanceof ApiError ? e.message : 'Could not add this screen'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function assignPlaylist(id: string, playlistId: string | null) {
    const body: DeviceUpdateBody = playlistId
      ? { playlist_id: playlistId }
      : { clear_playlist: true }
    const updated = await api.update(id, body)
    const row = items.value.find((d) => d.id === id)
    if (row) row.playlist_id = updated.playlist_id
  }

  onMounted(refresh)

  return { items, isLoading, isSaving, error, claimError, refresh, claim, assignPlaylist }
}
