import { request } from '@/api/request'
import type { DeviceSettingRead, PowerStatusRead } from '@/types/api'

/** One route handles every setting — volume today, brightness/power schedule/app lock/
 *  touchscreen lock later — because validation lives server-side in a key registry, not in
 *  a per-setting endpoint. Adding a setting never means adding a method here. */
export function useDeviceSettingsApi() {
  return {
    list: (deviceId: string) =>
      request<DeviceSettingRead[]>('GET', `/devices/${deviceId}/settings`),
    set: (deviceId: string, key: string, value: unknown) =>
      request<DeviceSettingRead>('PUT', `/devices/${deviceId}/settings/${key}`, { value }),
    /** Power is the exception to "one generic route": the state shown is resolved server-side
     *  from the schedule and override (services/power.py), and overriding works out its own
     *  end time — neither is a plain stored value. */
    power: (deviceId: string) => request<PowerStatusRead>('GET', `/devices/${deviceId}/power`),
    overridePower: (deviceId: string, state: 'on' | 'off') =>
      request<PowerStatusRead>('PUT', `/devices/${deviceId}/power/override`, { state }),
    resumePower: (deviceId: string) =>
      request<PowerStatusRead>('DELETE', `/devices/${deviceId}/power/override`),
  }
}
