import { request } from '@/api/request'
import type { AccountRead, LoginBody, MeResponse } from '@/types/api'

/** Transport only: call, parse, type, return. No loading state, no business rules. No signup
 *  here either — accounts are issued by a platform admin (see useAdminApi). */
export function useAuthApi() {
  return {
    me: () => request<MeResponse>('GET', '/me'),
    login: (body: LoginBody) => request<MeResponse>('POST', '/auth/login', body),
    logout: () => request<void>('POST', '/auth/logout'),
    /** Account-wide settings. Owner-only. */
    updateAccount: (body: { default_timezone?: string }) => request<AccountRead>('PATCH', '/account', body),
  }
}
