import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { AccountRead, UserRead } from '@/types/api'

/**
 * Shared state only. No HTTP here — hooks call API hooks and write into the store.
 *
 * The session itself is an HttpOnly cookie, so nothing in here is the credential; this is
 * a cache of who the backend says we are.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserRead | null>(null)
  const account = ref<AccountRead | null>(null)
  /** null means unrestricted (owner). A manager gets the explicit list. */
  const deviceIds = ref<string[] | null>(null)
  /** Whether /me has been answered at least once this page load. */
  const resolved = ref(false)

  return { user, account, deviceIds, resolved }
})
