import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useMediaApi } from '@/api/useMediaApi'
import type { MediaKind, MediaRead } from '@/types/api'

/** The library list: loading, filtering and refresh. */
export function useMedia() {
  const api = useMediaApi()

  const items = ref<MediaRead[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const filter = ref<MediaKind | 'all'>('all')

  const visible = computed(() =>
    filter.value === 'all' ? items.value : items.value.filter((m) => m.kind === filter.value),
  )
  const counts = computed(() => ({
    all: items.value.length,
    image: items.value.filter((m) => m.kind === 'image').length,
    video: items.value.filter((m) => m.kind === 'video').length,
  }))

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load the library'
    } finally {
      isLoading.value = false
    }
  }

  /** Prepend, so a just-finished upload appears at the top without a full refetch. */
  function prepend(media: MediaRead) {
    items.value = [media, ...items.value.filter((m) => m.id !== media.id)]
  }

  onMounted(refresh)

  return { items, visible, counts, filter, isLoading, error, refresh, prepend }
}
