import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useScheduleApi } from '@/api/useScheduleApi'
import type { ResolutionRead, ScheduleRead, ScheduleUpdateBody, ScheduleWrite } from '@/types/api'

export function useSchedules(deviceId: string) {
  const api = useScheduleApi()

  const schedules = ref<ScheduleRead[]>([])
  const resolution = ref<ResolutionRead | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const formError = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      // Both together: the rule list is not much use without showing what it currently
      // resolves to, which is the question anyone editing a schedule actually has.
      const [list, now] = await Promise.all([api.list(deviceId), api.now(deviceId)])
      schedules.value = list
      resolution.value = now
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load schedules'
    } finally {
      isLoading.value = false
    }
  }

  async function run<T>(fn: () => Promise<T>): Promise<boolean> {
    isSaving.value = true
    formError.value = null
    try {
      await fn()
      await refresh()
      return true
    } catch (e) {
      // 422s arrive already explaining themselves ("start and end must differ…").
      formError.value = e instanceof ApiError ? e.message : 'Something went wrong'
      return false
    } finally {
      isSaving.value = false
    }
  }

  const create = (body: ScheduleWrite) => run(() => api.create(deviceId, body))
  const update = (id: string, body: ScheduleUpdateBody) => run(() => api.update(id, body))
  const remove = (id: string) => run(() => api.remove(id))

  onMounted(refresh)

  return { schedules, resolution, isLoading, isSaving, error, formError, refresh, create, update, remove }
}
