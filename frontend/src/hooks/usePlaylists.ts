import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import type { PlaylistSummary } from '@/types/api'

export function usePlaylists() {
  const api = usePlaylistApi()

  const items = ref<PlaylistSummary[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const isCreating = ref(false)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load playlists'
    } finally {
      isLoading.value = false
    }
  }

  /** Returns the new playlist's id so the container can navigate straight into it. */
  async function create(name: string): Promise<string | null> {
    isCreating.value = true
    error.value = null
    try {
      const created = await api.create(name)
      await refresh()
      return created.id
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not create the playlist'
      return null
    } finally {
      isCreating.value = false
    }
  }

  onMounted(refresh)

  return { items, isLoading, isCreating, error, refresh, create }
}
