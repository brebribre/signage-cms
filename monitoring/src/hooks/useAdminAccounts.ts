import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useAdminApi } from '@/api/useAdminApi'
import type { AdminAccountCreateBody, AdminAccountRead, AdminLimitsUpdateBody } from '@/types/api'

/** The list of every customer account, and the two things done to one: make it, and change
 *  its limits. */
export function useAdminAccounts() {
  const api = useAdminApi()

  const accounts = ref<AdminAccountRead[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const formError = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      accounts.value = await api.listAccounts()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load accounts'
    } finally {
      isLoading.value = false
    }
  }

  async function run<T>(fn: () => Promise<T>): Promise<boolean> {
    isSaving.value = true
    formError.value = null
    try {
      await fn()
      await refresh()
      return true
    } catch (e) {
      // A 409 already says what went wrong — "That username is taken" — so it is shown as it came.
      formError.value = e instanceof ApiError ? e.message : 'Something went wrong'
      return false
    } finally {
      isSaving.value = false
    }
  }

  const create = (body: AdminAccountCreateBody) => run(() => api.createAccount(body))
  const setLimits = (id: string, body: AdminLimitsUpdateBody) => run(() => api.setLimits(id, body))

  onMounted(refresh)

  return { accounts, isLoading, isSaving, error, formError, refresh, create, setLimits }
}
