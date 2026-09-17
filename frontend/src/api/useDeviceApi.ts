import { request } from '@/api/request'
import type {
  ClaimBody,
  DeviceRead,
  DeviceResolutionRead,
  DeviceUpdateBody,
  DeviceUpdateVersionBody,
  ProbeResponse,
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
    /** What every reachable device is playing right now — read-only; Campaign is what changes
     *  it. */
    resolved: () => request<DeviceResolutionRead[]>('GET', '/devices/resolved'),
    /** A human types the code shown on the screen. */
    claim: (body: ClaimBody) => request<DeviceRead>('POST', '/devices/claim', body),
    update: (id: string, body: DeviceUpdateBody) =>
      request<DeviceRead>('PATCH', `/devices/${id}`, body),
    /** Asks the screen to check in right now. Returns a baseline to watch — see
     *  useDeviceDetail.ts's probe(), which does the actual watching. */
    probe: (id: string) => request<ProbeResponse>('POST', `/devices/${id}/probe`),
    /** Pins this one screen to a specific build, independent of the fleet rollout. Owner-only,
     *  same as the rest of player build management. */
    setForcedUpdate: (id: string, body: DeviceUpdateVersionBody) =>
      request<DeviceRead>('POST', `/devices/${id}/update`, body),
    /** Cancels a pending single-device update before the screen has picked it up. */
    cancelForcedUpdate: (id: string) => request<DeviceRead>('DELETE', `/devices/${id}/update`),
    /** Starts the disconnect handshake: the screen is told on its next request and resets
     *  itself; the row disappears (GET → 404) once it has heard. See useDeviceDetail.disconnect. */
    disconnect: (id: string) => request<DeviceRead>('POST', `/devices/${id}/disconnect`),
    /** Removes the row without waiting for the screen — the fallback when it never answers. */
    remove: (id: string) => request<void>('DELETE', `/devices/${id}`),
  }
}
