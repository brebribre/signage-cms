import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useOperationsApi } from '@/api/useOperationsApi'
import type { DeviceHealthRead, StorageRead } from '@/types/api'

/** Refreshed periodically: a health page that needs a manual reload to tell you a screen
 *  went down is not a health page. */
const REFRESH_MS = 30_000

export function useFleetHealth() {
  const api = useOperationsApi()

  const devices = ref<DeviceHealthRead[]>([])
  const storage = ref<StorageRead | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const offline = computed(() => devices.value.filter((d) => !d.is_online))
  const withErrors = computed(() => devices.value.filter((d) => d.error_count_24h > 0))

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      const [health, store] = await Promise.all([api.fleetHealth(), api.storage()])
      devices.value = health
      storage.value = store
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load fleet health'
    } finally {
      isLoading.value = false
    }
  }

  let timer: number | undefined
  onMounted(() => {
    refresh()
    timer = window.setInterval(refresh, REFRESH_MS)
  })
  // Cleared on unmount, or the interval keeps firing against a page nobody is looking at.
  onUnmounted(() => window.clearInterval(timer))

  return { devices, storage, offline, withErrors, isLoading, error, refresh }
}
