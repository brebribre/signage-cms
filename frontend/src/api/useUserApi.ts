import { request } from '@/api/request'
import type { AccountUserRead, ManagerCreateBody } from '@/types/api'

/** Owner-only endpoints. The server enforces that; hiding the nav entry is a courtesy. */
export function useUserApi() {
  return {
    list: () => request<AccountUserRead[]>('GET', '/users'),
    create: (body: ManagerCreateBody) => request<AccountUserRead>('POST', '/users', body),
    update: (id: string, body: { display_name?: string; is_active?: boolean }) =>
      request<AccountUserRead>('PATCH', `/users/${id}`, body),
    setPassword: (id: string, password: string) =>
      request<void>('POST', `/users/${id}/password`, { password }),
    setDevices: (id: string, deviceIds: string[]) =>
      request<AccountUserRead>('PUT', `/users/${id}/devices`, { device_ids: deviceIds }),
    remove: (id: string) => request<void>('DELETE', `/users/${id}`),
  }
}
