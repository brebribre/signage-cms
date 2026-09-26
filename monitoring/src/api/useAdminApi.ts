import { request } from '@/api/request'
import type {
  AdminAccountCreateBody,
  AdminAccountRead,
  AdminLimitsUpdateBody,
  InfrastructureRead,
  LoginBody,
  StaffRead,
} from '@/types/api'

/** Transport only. Everything this app calls lives under /admin/*, and the server refuses
 *  anyone who isn't staff on every one of them — and checks again, per call, what that
 *  particular member of staff may do. */
export function useAdminApi() {
  return {
    // Sign-in. Same username and password as the CMS; anyone who isn't staff gets a plain 401.
    me: () => request<StaffRead>('GET', '/admin/me'),
    login: (body: LoginBody) => request<StaffRead>('POST', '/admin/auth/login', body),
    logout: () => request<void>('POST', '/admin/auth/logout'),

    // Accounts of every kind.
    listAccounts: () => request<AdminAccountRead[]>('GET', '/admin/accounts'),
    createAccount: (body: AdminAccountCreateBody) =>
      request<AdminAccountRead>('POST', '/admin/accounts', body),
    /** A temporary password for the account's main user; they choose their own at next sign-in. */
    resetPassword: (id: string, password: string) =>
      request<AdminAccountRead>('POST', `/admin/accounts/${id}/password`, { password }),
    setLimits: (id: string, body: AdminLimitsUpdateBody) =>
      request<AdminAccountRead>('PATCH', `/admin/accounts/${id}`, body),

    // The platform in numbers: bucket size, people, screens. Read-only.
    infrastructure: () => request<InfrastructureRead>('GET', '/admin/infrastructure'),
  }
}
