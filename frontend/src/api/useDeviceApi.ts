import { request } from '@/api/request'
import type {
  BulkAssignPlaylistBody,
  BulkAssignPlaylistResponse,
  ClaimBody,
  DeviceRead,
  DeviceUpdateBody,
  PairStartResponse,
} from '@/types/api'

/**
 * The CMS side only. `/devices/pair` and `/devices/pair/{token}` belong to the device
 * itself (the Android app in Phase 12a) and are never called from this app — the browser
 * never has a device's poll token.
 */
export function useDeviceApi() {
  return {
    list: () => request<DeviceRead[]>('GET', '/devices'),
    get: (id: string) => request<DeviceRead>('GET', `/devices/${id}`),
    /** A human types the code shown on the screen. */
    claim: (body: ClaimBody) => request<DeviceRead>('POST', '/devices/claim', body),
    update: (id: string, body: DeviceUpdateBody) =>
      request<DeviceRead>('PATCH', `/devices/${id}`, body),
    /** One playlist across many screens in a single request/transaction. */
    bulkAssignPlaylist: (body: BulkAssignPlaylistBody) =>
      request<BulkAssignPlaylistResponse>('POST', '/devices/bulk-assign-playlist', body),
    /** Revokes the token and returns a fresh pairing code — the screen falls back to
     *  showing it, same as a first boot. */
    unpair: (id: string) => request<PairStartResponse>('POST', `/devices/${id}/unpair`),
    remove: (id: string) => request<void>('DELETE', `/devices/${id}`),
  }
}
