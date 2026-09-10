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
  const savingKey = ref<string | null>(null)
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

  /** Returns whether it took, so the row can show its own loading state and checkmark rather
   *  than silently succeeding or silently swallowing a failure. */
  async function set(key: string, newValue: unknown): Promise<boolean> {
    savingKey.value = key
    error.value = null
    try {
      const row = await api.set(deviceId, key, newValue)
      const existing = items.value.find((s) => s.key === key)
      if (existing) existing.value = row.value
      else items.value.push(row)
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not update this setting'
      return false
    } finally {
      savingKey.value = null
    }
  }

  onMounted(refresh)

  return { items, isLoading, savingKey, error, refresh, value, set }
}
