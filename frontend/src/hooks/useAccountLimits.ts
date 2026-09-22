import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useOperationsApi } from '@/api/useOperationsApi'
import type { LimitsRead } from '@/types/api'

/** The account's plan as figures: screens used against the limit, storage used against the
 *  quota. Read-only — the limits are set by Paskall, not here. `null` for a limit means
 *  unlimited. */
export function useAccountLimits() {
  const api = useOperationsApi()
  const limits = ref<LimitsRead | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      limits.value = await api.limits()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load the plan limits'
    } finally {
      isLoading.value = false
    }
  }
  onMounted(refresh)

  /** 0–1 of the limit used; null when unlimited. */
  const screensFraction = computed(() => {
    const l = limits.value
    return l && l.max_screens ? Math.min(1, l.screens_used / l.max_screens) : null
  })
  const storageFraction = computed(() => {
    const l = limits.value
    return l && l.storage_quota_bytes ? Math.min(1, l.storage_used_bytes / l.storage_quota_bytes) : null
  })

  return { limits, isLoading, error, refresh, screensFraction, storageFraction }
}
