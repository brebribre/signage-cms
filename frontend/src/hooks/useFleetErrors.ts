import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useOperationsApi } from '@/api/useOperationsApi'
import type { FleetEventRead } from '@/types/api'

/** The newest errors across every screen the user can reach — the Overview's Errors tab. */
export function useFleetErrors() {
  const api = useOperationsApi()
  const items = ref<FleetEventRead[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.errors()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load errors'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(refresh)
  return { items, isLoading, error, refresh }
}
