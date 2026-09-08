import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useMediaApi } from '@/api/useMediaApi'
import type { MediaDetail } from '@/types/api'

export function useMediaDetail(id: string) {
  const api = useMediaApi()

  const media = ref<MediaDetail | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const deleteError = ref<string | null>(null)
  const isDeleting = ref(false)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      media.value = await api.get(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this file'
    } finally {
      isLoading.value = false
    }
  }

  /** True when it was deleted, so the container knows to navigate away. */
  async function remove(): Promise<boolean> {
    isDeleting.value = true
    deleteError.value = null
    try {
      await api.remove(id)
      return true
    } catch (e) {
      // A 409 arrives already naming the playlists — "Used in Lobby Loop — remove it there
      // first" — so it is shown as-is rather than replaced with "Conflict".
      deleteError.value = e instanceof ApiError ? e.message : 'Could not delete this file'
      return false
    } finally {
      isDeleting.value = false
    }
  }

  onMounted(refresh)

  return { media, isLoading, error, deleteError, isDeleting, refresh, remove }
}
