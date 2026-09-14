import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import { usePlayerRolloutApi } from '@/api/usePlayerRolloutApi'
import type { PlayerReleaseRead, PlayerRolloutRead } from '@/types/api'

/** Every uploaded build, the rollout timeline, and scheduling a new one. Owner-only —
 *  the route itself is gated the same way Users is. */
export function usePlayerRollouts() {
  const api = usePlayerRolloutApi()
  const deviceApi = useDeviceApi()

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
      error.value = e instanceof ApiError ? e.message : 'Could not load software updates'
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

  /** A release onto chosen screens only, rather than the whole fleet — each one pinned to it,
   *  now or from `scheduledAt`. A pin wins over the fleet rollout for that screen (see backend
   *  device_sync.available_update). One request per screen, fired together; returns whether
   *  every one took. */
  async function pinDevices(version: string, deviceIds: string[], scheduledAt: string | null): Promise<boolean> {
    isSaving.value = true
    error.value = null
    const results = await Promise.allSettled(
      deviceIds.map((id) => deviceApi.setForcedUpdate(id, { version, scheduled_at: scheduledAt })),
    )
    const failed = results.filter((r) => r.status === 'rejected').length
    if (failed) error.value = `${failed} of ${deviceIds.length} screens couldn't be updated`
    isSaving.value = false
    return failed === 0
  }

  /** Drops a pending pin, so the screen follows the fleet rollout again. */
  async function cancelPin(deviceId: string): Promise<boolean> {
    isSaving.value = true
    error.value = null
    try {
      await deviceApi.cancelForcedUpdate(deviceId)
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not cancel this update'
      return false
    } finally {
      isSaving.value = false
    }
  }

  onMounted(refresh)

  return { releases, rollouts, isLoading, isSaving, error, refresh, schedule, cancel, pinDevices, cancelPin }
}
