import { request } from '@/api/request'
import type { AccountRead, LoginBody, MeResponse, SignupBody } from '@/types/api'

/** Transport only: call, parse, type, return. No loading state, no business rules. */
export function useAuthApi() {
  return {
    me: () => request<MeResponse>('GET', '/me'),
    login: (body: LoginBody) => request<MeResponse>('POST', '/auth/login', body),
    signup: (body: SignupBody) => request<MeResponse>('POST', '/auth/signup', body),
    logout: () => request<void>('POST', '/auth/logout'),
    /** Account-wide settings. Owner-only. */
    updateAccount: (body: { default_timezone?: string }) => request<AccountRead>('PATCH', '/account', body),
  }
}
