import { computed, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useReviewApi } from '@/api/useReviewApi'
import type { ReviewRead } from '@/types/api'

/** One count for the whole app: the sidebar badge and the Reviews page read the same number,
 *  and anything that parks or decides a review bumps it. Module state, not a store — it is a
 *  cache of one integer. */
const pendingCount = ref(0)
let countLoaded = false

export function useReviewBadge() {
  const api = useReviewApi()
  async function refreshCount() {
    try {
      pendingCount.value = (await api.pendingCount()).count
      countLoaded = true
    } catch {
      /* the badge is decoration; a failed count just stays as it was */
    }
  }
  function ensureCount() {
    if (!countLoaded) void refreshCount()
  }
  return { pendingCount, refreshCount, ensureCount }
}

export function useReviews() {
  const api = useReviewApi()
  const { refreshCount } = useReviewBadge()

  const items = ref<ReviewRead[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  /** Which review a decision is in flight for, so only its buttons show a spinner. */
  const actingOn = ref<string | null>(null)
  const actionError = ref<string | null>(null)

  const pending = computed(() => items.value.filter((r) => r.status === 'pending'))
  const decided = computed(() => items.value.filter((r) => r.status !== 'pending'))

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
      pendingCount.value = pending.value.length
      countLoaded = true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load reviews'
    } finally {
      isLoading.value = false
    }
  }

  async function act(id: string, fn: () => Promise<ReviewRead>): Promise<boolean> {
    actingOn.value = id
    actionError.value = null
    try {
      const updated = await fn()
      items.value = items.value.map((r) => (r.id === updated.id ? updated : r))
      pendingCount.value = pending.value.length
      return true
    } catch (e) {
      actionError.value = e instanceof ApiError ? e.message : 'Could not update this review'
      return false
    } finally {
      actingOn.value = null
    }
  }

  const approve = (id: string, note?: string) => act(id, () => api.approve(id, note))
  const reject = (id: string, note?: string) => act(id, () => api.reject(id, note))
  const withdraw = (id: string) => act(id, () => api.withdraw(id))

  return { items, pending, decided, isLoading, error, actingOn, actionError, refresh, refreshCount, approve, reject, withdraw }
}
