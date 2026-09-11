import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useScheduleApi } from '@/api/useScheduleApi'
import type { ResolutionRead } from '@/types/api'

/** What a device is playing right now — resolved server-side from whatever Campaign covers
 *  it, exactly as the manifest does it. Read-only; assignment happens only in Campaigns. */
export function useDeviceResolution(deviceId: string) {
  const api = useScheduleApi()

  const resolution = ref<ResolutionRead | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      resolution.value = await api.now(deviceId)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load what this screen is playing'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(refresh)

  return { resolution, isLoading, error, refresh }
}
