import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import { useUserApi } from '@/api/useUserApi'
import type { AccountUserRead, DeviceRead, ManagerCreateBody } from '@/types/api'

export function useUsers() {
  const api = useUserApi()
  const deviceApi = useDeviceApi()

  const users = ref<AccountUserRead[]>([])
  const devices = ref<DeviceRead[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const formError = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      // Both, because the grant checkboxes are useless without the device list.
      const [u, d] = await Promise.all([api.list(), deviceApi.list()])
      users.value = u
      devices.value = d
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load users'
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
      // 409s arrive already explaining themselves — "You cannot delete your own account",
      // "That username is taken" — so they are shown as they came.
      formError.value = e instanceof ApiError ? e.message : 'Something went wrong'
      return false
    } finally {
      isSaving.value = false
    }
  }

  const create = (body: ManagerCreateBody) => run(() => api.create(body))
  const setActive = (id: string, isActive: boolean) => run(() => api.update(id, { is_active: isActive }))
  const setDevices = (id: string, ids: string[]) => run(() => api.setDevices(id, ids))
  const setPassword = (id: string, password: string) => run(() => api.setPassword(id, password))
  const remove = (id: string) => run(() => api.remove(id))

  onMounted(refresh)

  return {
    users, devices, isLoading, isSaving, error, formError,
    refresh, create, setActive, setDevices, setPassword, remove,
  }
}
