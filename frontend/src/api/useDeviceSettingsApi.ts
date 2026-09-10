import { request } from '@/api/request'
import type { DeviceSettingRead } from '@/types/api'

/** One route handles every setting — volume today, brightness/power schedule/app lock/
 *  touchscreen lock later — because validation lives server-side in a key registry, not in
 *  a per-setting endpoint. Adding a setting never means adding a method here. */
export function useDeviceSettingsApi() {
  return {
    list: (deviceId: string) =>
      request<DeviceSettingRead[]>('GET', `/devices/${deviceId}/settings`),
    set: (deviceId: string, key: string, value: unknown) =>
      request<DeviceSettingRead>('PUT', `/devices/${deviceId}/settings/${key}`, { value }),
  }
}
