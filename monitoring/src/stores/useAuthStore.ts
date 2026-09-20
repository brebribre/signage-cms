import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { UserRead } from '@/types/api'

/**
 * Shared state only. No HTTP here — hooks call API hooks and write into the store.
 *
 * The session itself is an HttpOnly cookie, so nothing in here is the credential; this is a
 * cache of who the backend says we are — and here, that is always a platform admin.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserRead | null>(null)
  /** Whether /admin/me has been answered at least once this page load. */
  const resolved = ref(false)

  return { user, resolved }
})
