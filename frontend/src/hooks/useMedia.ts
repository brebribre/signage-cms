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

  /** `silent` skips the loading flag — for the background poll while a video is being
   *  optimised, where flashing the grid to skeletons every few seconds would be worse than the
   *  badge it's refreshing. */
  async function refresh(silent = false) {
    if (!silent) isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load the library'
    } finally {
      if (!silent) isLoading.value = false
    }
  }

  /** Prepend, so a just-finished upload appears at the top without a full refetch. */
  function prepend(media: MediaRead) {
    items.value = [media, ...items.value.filter((m) => m.id !== media.id)]
  }

  /**
   * Deletes each file — four at a time, so a big selection doesn't crawl — and reports what
   * happened to every one of them.
   *
   * Not all-or-nothing, on purpose: the server refuses a file that is still in a playlist (and,
   * for a manager, one somebody else uploaded), and one refusal shouldn't keep the other
   * nineteen in the library. Deleted files leave the list at once; refused ones stay, with the
   * server's own reason ("Used in Lobby Loop — remove it there first").
   */
  async function removeMany(ids: string[]): Promise<{ deleted: number; failed: { filename: string; reason: string }[] }> {
    const failed: { filename: string; reason: string }[] = []
    const gone = new Set<string>()
    const queue = [...ids]
    const worker = async () => {
      for (let id = queue.shift(); id !== undefined; id = queue.shift()) {
        try {
          await api.remove(id)
          gone.add(id)
        } catch (e) {
          const filename = items.value.find((m) => m.id === id)?.filename ?? 'A file'
          failed.push({ filename, reason: e instanceof ApiError ? e.message : 'Could not delete it' })
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(4, ids.length) }, worker))
    items.value = items.value.filter((m) => !gone.has(m.id))
    return { deleted: gone.size, failed }
  }

  onMounted(refresh)

  return { items, visible, counts, filter, isLoading, error, refresh, prepend, removeMany }
}
