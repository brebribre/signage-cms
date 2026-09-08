import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useOperationsApi } from '@/api/useOperationsApi'
import type { DeviceEventRead, PlayEventRead } from '@/types/api'

/** Recent errors and proof-of-play for one screen. */
export function useDeviceActivity(deviceId: string) {
  const api = useOperationsApi()

  const events = ref<DeviceEventRead[]>([])
  const plays = ref<PlayEventRead[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      const [e, p] = await Promise.all([api.events(deviceId), api.plays(deviceId)])
      events.value = e
      plays.value = p
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Could not load activity'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(refresh)
  return { events, plays, isLoading, error, refresh }
}
