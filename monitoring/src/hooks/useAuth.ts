import { computed, ref } from 'vue'

import { useAdminApi } from '@/api/useAdminApi'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/useAuthStore'
import type { LoginBody, UserRead } from '@/types/api'

/**
 * Containers reach the auth store through here, never directly. Being "signed in" here means
 * /admin/me answered 200, which it only does for a platform admin — so there is no separate
 * "is admin" check anywhere in this app: signed in *is* admin.
 */
export function useAuth() {
  const store = useAuthStore()
  const api = useAdminApi()

  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const user = computed(() => store.user)
  const isSignedIn = computed(() => store.user !== null)

  function apply(me: UserRead) {
    store.user = me
    store.resolved = true
  }

  function clear() {
    store.user = null
    store.resolved = true
  }

  /** Ask the backend who we are — answered by /admin/me, never by inspecting storage, because
   *  the cookie is HttpOnly. Resolved once per page load; the guard calls it first. */
  async function resolve(force = false) {
    if (store.resolved && !force) return
    try {
      apply(await api.me())
    } catch {
      clear()
    }
  }

  async function login(body: LoginBody): Promise<boolean> {
    isLoading.value = true
    error.value = null
    try {
      apply(await api.login(body))
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Something went wrong'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      await api.logout()
    } finally {
      // Clear locally whatever the server said: a failed logout must not leave the UI
      // claiming to be signed in.
      clear()
    }
  }

  return { user, isSignedIn, isLoading, error, resolve, login, logout }
}
