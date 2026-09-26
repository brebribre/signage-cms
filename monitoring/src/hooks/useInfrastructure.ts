import { onMounted, onUnmounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useAdminApi } from '@/api/useAdminApi'
import type { InfrastructureRead } from '@/types/api'

/** How often the page asks again while open. Screens come and go by the minute; the bucket
 *  itself is re-measured by the server at most every five, whatever this is. */
const REFRESH_MS = 60_000

/** The Infrastructure page's numbers, kept fresh while the page is open. */
export function useInfrastructure() {
  const api = useAdminApi()

  const data = ref<InfrastructureRead | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      data.value = await api.infrastructure()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load the numbers'
    } finally {
      isLoading.value = false
    }
  }

  let timer: ReturnType<typeof setInterval> | undefined
  onMounted(() => {
    refresh()
    timer = setInterval(() => {
      // A hidden tab has nobody looking; it catches up the moment it is shown again.
      if (document.visibilityState === 'visible') refresh()
    }, REFRESH_MS)
  })
  onUnmounted(() => clearInterval(timer))

  return { data, isLoading, error, refresh }
}
