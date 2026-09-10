import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useScheduleApi } from '@/api/useScheduleApi'
import type { ResolutionRead, ScheduleRead } from '@/types/api'

/** Read-only: a device's schedule rules and what they currently resolve to. Creating or
 *  changing a rule happens only in Campaigns. */
export function useSchedules(deviceId: string) {
  const api = useScheduleApi()

  const schedules = ref<ScheduleRead[]>([])
  const resolution = ref<ResolutionRead | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      // Both together: the rule list is not much use without showing what it currently
      // resolves to.
      const [list, now] = await Promise.all([api.list(deviceId), api.now(deviceId)])
      schedules.value = list
      resolution.value = now
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load schedules'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(refresh)

  return { schedules, resolution, isLoading, error, refresh }
}
