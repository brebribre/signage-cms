import { computed, ref } from 'vue'

import { useAuthApi } from '@/api/useAuthApi'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/useAuthStore'
import type { LoginBody, MeResponse, SignupBody } from '@/types/api'

/**
 * Containers reach the auth store through here, never directly — that keeps the container
 * rule to one thing: call hooks.
 */
export function useAuth() {
  const store = useAuthStore()
  const api = useAuthApi()

  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const user = computed(() => store.user)
  const account = computed(() => store.account)
  const isSignedIn = computed(() => store.user !== null)
  const isOwner = computed(() => store.user?.role === 'owner')

  function apply(me: MeResponse) {
    store.user = me.user
    store.account = me.account
    store.deviceIds = me.device_ids
    store.resolved = true
  }

  function clear() {
    store.user = null
    store.account = null
    store.deviceIds = null
    store.resolved = true
  }

  /**
   * Ask the backend who we are. "Am I signed in?" is always answered by /me returning 200
   * vs 401 — never by inspecting storage, because the cookie is HttpOnly and unreadable.
   *
   * Resolved once per page load; the guard calls it before the first navigation.
   */
  async function resolve(force = false) {
    if (store.resolved && !force) return
    try {
      apply(await api.me())
    } catch {
      clear()
    }
  }

  async function submit(fn: () => Promise<MeResponse>) {
    isLoading.value = true
    error.value = null
    try {
      apply(await fn())
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Something went wrong'
      return false
    } finally {
      isLoading.value = false
    }
  }

  const login = (body: LoginBody) => submit(() => api.login(body))
  const signup = (body: SignupBody) => submit(() => api.signup(body))

  async function logout() {
    try {
      await api.logout()
    } finally {
      // Clear locally whatever the server said: a failed logout must not leave the UI
      // claiming to be signed in.
      clear()
    }
  }

  return { user, account, isSignedIn, isOwner, isLoading, error, resolve, login, signup, logout }
}
