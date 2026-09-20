import { request } from '@/api/request'
import type {
  AdminAccountCreateBody,
  AdminAccountRead,
  AdminLimitsUpdateBody,
  LoginBody,
  UserRead,
} from '@/types/api'

/** Transport only. Everything this app calls lives under /admin/*, and the server refuses
 *  anyone who isn't a platform admin on every one of them. */
export function useAdminApi() {
  return {
    // Sign-in. Same username and password as the CMS; a non-admin gets a plain 401.
    me: () => request<UserRead>('GET', '/admin/me'),
    login: (body: LoginBody) => request<UserRead>('POST', '/admin/auth/login', body),
    logout: () => request<void>('POST', '/admin/auth/logout'),

    // Customer accounts.
    listAccounts: () => request<AdminAccountRead[]>('GET', '/admin/accounts'),
    createAccount: (body: AdminAccountCreateBody) =>
      request<AdminAccountRead>('POST', '/admin/accounts', body),
    setLimits: (id: string, body: AdminLimitsUpdateBody) =>
      request<AdminAccountRead>('PATCH', `/admin/accounts/${id}`, body),
  }
}
