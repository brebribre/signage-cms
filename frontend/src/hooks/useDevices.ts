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
  /** Set while a just-claimed screen is being waited on, so the UI can show the handshake
   *  rather than a spinner that means nothing. */
  const connecting = ref<{ id: string; name: string; connected: boolean } | null>(null)

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

  /** How long to wait for the screen to collect its token before saying so. The device polls
   *  every 5s, so this is generous — it is about telling the truth when something is wrong,
   *  not about being impatient. */
  const CONNECT_TIMEOUT_MS = 30_000

  /**
   * Claim a screen, then wait until it has actually connected.
   *
   * The claim itself returns immediately, but at that moment the screen still knows nothing —
   * it collects its token on its next poll. Reporting success there is technically true and
   * practically misleading: people walk away from a screen that has not started. So this
   * polls until `paired_at` is set, which is the server's record that the device really came
   * and took its credential.
   */
  async function claim(body: ClaimBody): Promise<boolean> {
    isSaving.value = true
    claimError.value = null
    connecting.value = null
    try {
      const device = await api.claim(body)
      connecting.value = { id: device.id, name: device.name, connected: false }

      const deadline = Date.now() + CONNECT_TIMEOUT_MS
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 1500))
        const fresh = await api.get(device.id)
        if (fresh.paired_at) {
          connecting.value = { id: device.id, name: device.name, connected: true }
          await refresh()
          return true
        }
      }

      // Claimed, but the screen never came back for its token. The row exists and the code
      // is spent, so this is not a failure to undo — it is a screen that needs looking at.
      claimError.value =
        `Added, but ${device.name} has not connected yet. It should pick this up within a ` +
        `few seconds — check the screen is still showing the code and has a network.`
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

  /** Returns whether it took, so the row can show its own loading state and checkmark
   *  rather than silently succeeding or silently swallowing a failure. */
  async function assignPlaylist(id: string, playlistId: string | null): Promise<boolean> {
    const body: DeviceUpdateBody = playlistId
      ? { playlist_id: playlistId }
      : { clear_playlist: true }
    try {
      const updated = await api.update(id, body)
      const row = items.value.find((d) => d.id === id)
      if (row) row.playlist_id = updated.playlist_id
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not update playlist'
      return false
    }
  }

  /** Same as `assignPlaylist`, for many devices in one request. Ids the server skipped
   *  (unreachable by this user) come back so the caller can say which ones didn't take. */
  async function bulkAssignPlaylist(
    ids: string[], playlistId: string | null
  ): Promise<{ ok: boolean; skippedIds: string[] }> {
    try {
      const res = await api.bulkAssignPlaylist({
        device_ids: ids,
        ...(playlistId ? { playlist_id: playlistId } : { clear_playlist: true }),
      })
      for (const updated of res.updated) {
        const row = items.value.find((d) => d.id === updated.id)
        if (row) row.playlist_id = updated.playlist_id
      }
      return { ok: true, skippedIds: res.skipped_ids }
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not update screens'
      return { ok: false, skippedIds: [] }
    }
  }

  onMounted(refresh)

  return {
    items, isLoading, isSaving, error, claimError, connecting,
    refresh, claim, assignPlaylist, bulkAssignPlaylist,
  }
}
