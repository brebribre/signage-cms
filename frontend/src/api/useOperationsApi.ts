import { request } from '@/api/request'
import type {
  DeviceEventRead,
  DeviceHealthRead,
  PlayEventRead,
  StorageRead,
} from '@/types/api'

export function useOperationsApi() {
  return {
    storage: () => request<StorageRead>('GET', '/storage'),
    fleetHealth: () => request<DeviceHealthRead[]>('GET', '/health/devices'),
    events: (deviceId: string) =>
      request<DeviceEventRead[]>('GET', `/devices/${deviceId}/events`),
    plays: (deviceId: string) =>
      request<PlayEventRead[]>('GET', `/devices/${deviceId}/plays`),
  }
}
