import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceSettingsApi } from '@/api/useDeviceSettingsApi'
import type { DeviceSettingRead } from '@/types/api'

/** A device's remotely-configurable settings — volume today, more later by the same
 *  mechanism (see DeviceSettingsContainer.vue). Generic over the key on purpose: this hook
 *  never needs to change when a new setting is added. */
export function useDeviceSettings(deviceId: string) {
  const api = useDeviceSettingsApi()

  const items = ref<DeviceSettingRead[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list(deviceId)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load settings'
    } finally {
      isLoading.value = false
    }
  }

  function value(key: string): unknown {
    return items.value.find((s) => s.key === key)?.value
  }

  /** What the device itself last reported for this key, or undefined before any heartbeat
   *  has said so. */
  function reportedValue(key: string): unknown {
    return items.value.find((s) => s.key === key)?.reported_value
  }

  /**
   * Saves every entry in one action. Each key is still its own backend request — there's no
   * bulk route — fired together rather than one at a time so a slow key doesn't hold up the
   * rest. Returns the keys that failed, so the caller can leave just those drafts dirty
   * instead of losing every pending change over one bad key.
   */
  async function setMany(entries: { key: string; value: unknown }[]): Promise<string[]> {
    isSaving.value = true
    error.value = null
    const failedKeys: string[] = []
    const results = await Promise.allSettled(
      entries.map((entry) => api.set(deviceId, entry.key, entry.value)),
    )
    results.forEach((result, i) => {
      const key = entries[i].key
      if (result.status === 'fulfilled') {
        const existing = items.value.find((s) => s.key === key)
        if (existing) Object.assign(existing, result.value)
        else items.value.push(result.value)
      } else {
        failedKeys.push(key)
      }
    })
    if (failedKeys.length) error.value = 'Could not save every setting'
    isSaving.value = false
    return failedKeys
  }

  onMounted(refresh)

  return { items, isLoading, isSaving, error, refresh, value, reportedValue, setMany }
}
