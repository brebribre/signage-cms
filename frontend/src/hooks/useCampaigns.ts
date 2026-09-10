import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useCampaignApi } from '@/api/useCampaignApi'
import type { CampaignSummary } from '@/types/api'

/** The campaign list: every playlist-on-schedule assignment across every screen, in one
 *  place — this is the only page that can create or change one. */
export function useCampaigns() {
  const api = useCampaignApi()

  const items = ref<CampaignSummary[]>([])
  const isLoading = ref(false)
  const isDeleting = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      items.value = await api.list()
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load campaigns'
    } finally {
      isLoading.value = false
    }
  }

  async function remove(id: string): Promise<boolean> {
    isDeleting.value = true
    try {
      await api.remove(id)
      await refresh()
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not delete the campaign'
      return false
    } finally {
      isDeleting.value = false
    }
  }

  onMounted(refresh)

  return { items, isLoading, isDeleting, error, refresh, remove }
}
