import { ref } from 'vue'

import { ApiError } from '@/api/request'
import { useAuthApi } from '@/api/useAuthApi'
import { useAuthStore } from '@/stores/useAuthStore'

/** Settings → General: account-wide settings, saved to the account and reflected in the signed-in
 *  session straight away, so everything reading `account` sees the new value without a reload. */
export function useAccountSettings() {
  const api = useAuthApi()
  const store = useAuthStore()
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function save(body: { default_timezone?: string }): Promise<boolean> {
    isSaving.value = true
    error.value = null
    try {
      store.account = await api.updateAccount(body)
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not save these settings'
      return false
    } finally {
      isSaving.value = false
    }
  }

  return { isSaving, error, save }
}
