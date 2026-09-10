import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlayerRolloutApi } from '@/api/usePlayerRolloutApi'
import type { PlayerReleaseRead, PlayerRolloutRead } from '@/types/api'

/** Every uploaded build, the rollout timeline, and scheduling a new one. Owner-only —
 *  the route itself is gated the same way Users is. */
export function usePlayerRollouts() {
  const api = usePlayerRolloutApi()

  const releases = ref<PlayerReleaseRead[]>([])
  const rollouts = ref<PlayerRolloutRead[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      const [r, ro] = await Promise.all([api.releases(), api.rollouts()])
      releases.value = r
      rollouts.value = ro
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load player updates'
    } finally {
      isLoading.value = false
    }
  }

  /** `scheduledAt` null publishes immediately. Returns whether it took. */
  async function schedule(version: string, scheduledAt: string | null): Promise<boolean> {
    isSaving.value = true
    error.value = null
    try {
      await api.schedule({ version, scheduled_at: scheduledAt })
      await refresh()
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not schedule this rollout'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function cancel(id: string): Promise<boolean> {
    isSaving.value = true
    error.value = null
    try {
      await api.cancel(id)
      await refresh()
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not cancel this rollout'
      return false
    } finally {
      isSaving.value = false
    }
  }

  onMounted(refresh)

  return { releases, rollouts, isLoading, isSaving, error, refresh, schedule, cancel }
}
