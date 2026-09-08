import { request } from '@/api/request'
import type { DeviceRead } from '@/types/api'

export function useDeviceApi() {
  return {
    list: () => request<DeviceRead[]>('GET', '/devices'),
  }
}
