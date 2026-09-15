import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceSettingsApi } from '@/api/useDeviceSettingsApi'
import type { PowerStatusRead } from '@/types/api'

/** A screen's resolved power state, and the two actions on it: "turn on/off now" and "resume
 *  schedule". Settings stages these like everything else and calls them on "Save changes";
 *  each resolves to whether it worked. */
export function useDevicePower(deviceId: string) {
  const api = useDeviceSettingsApi()

  const status = ref<PowerStatusRead | null>(null)
  const isActing = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    try {
      status.value = await api.power(deviceId)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load power'
    }
  }

  async function act(call: () => Promise<PowerStatusRead>): Promise<boolean> {
    isActing.value = true
    error.value = null
    try {
      status.value = await call()
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not change power'
      return false
    } finally {
      isActing.value = false
    }
  }

  const override = (state: 'on' | 'off') => act(() => api.overridePower(deviceId, state))
  const resume = () => act(() => api.resumePower(deviceId))

  onMounted(refresh)

  return { status, isActing, error, refresh, override, resume }
}
