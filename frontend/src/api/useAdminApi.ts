import { request } from '@/api/request'
import type { AdminAccountCreateBody, AdminAccountRead, AdminLimitsUpdateBody } from '@/types/api'

/** Fortu staff only. The server enforces that on every call; hiding the nav entry is a courtesy. */
export function useAdminApi() {
  return {
    listAccounts: () => request<AdminAccountRead[]>('GET', '/admin/accounts'),
    createAccount: (body: AdminAccountCreateBody) =>
      request<AdminAccountRead>('POST', '/admin/accounts', body),
    setLimits: (id: string, body: AdminLimitsUpdateBody) =>
      request<AdminAccountRead>('PATCH', `/admin/accounts/${id}`, body),
  }
}
