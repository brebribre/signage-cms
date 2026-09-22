import { request } from '@/api/request'
import type {
  DeviceEventRead,
  DeviceHealthRead,
  LimitsRead,
  PlayEventRead,
  StorageRead,
  FleetEventRead,
} from '@/types/api'

export function useOperationsApi() {
  return {
    storage: () => request<StorageRead>('GET', '/storage'),
    /** Screens and storage: used against allowed. */
    limits: () => request<LimitsRead>('GET', '/limits'),
    fleetHealth: () => request<DeviceHealthRead[]>('GET', '/health/devices'),
    events: (deviceId: string) =>
      request<DeviceEventRead[]>('GET', `/devices/${deviceId}/events`),
    /** The newest errors across every screen, each with its screen's name. */
    errors: () => request<FleetEventRead[]>('GET', '/events/errors'),
    plays: (deviceId: string) =>
      request<PlayEventRead[]>('GET', `/devices/${deviceId}/plays`),
  }
}
