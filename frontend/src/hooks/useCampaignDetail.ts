import { onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useCampaignApi } from '@/api/useCampaignApi'
import { useReviewBadge } from '@/hooks/useReviews'
import type { CampaignRead, CampaignWrite, ReviewRead } from '@/types/api'
import { isPendingReview } from '@/types/api'

/** One campaign, in create mode (`id` null) or edit mode. Both save through the same full
 *  `CampaignWrite` — a campaign's device list and rules are always saved as one set. */
export function useCampaignDetail(id: string | null) {
  const api = useCampaignApi()

  const campaign = ref<CampaignRead | null>(null)
  const isLoading = ref(!!id)
  const isSaving = ref(false)
  const isDeleting = ref(false)
  const error = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  const skippedDeviceIds = ref<string[]>([])
  /** Set when the last save or delete was parked for the owner instead of applied — every
   *  campaign change is, for a manager. The campaign itself has not changed. */
  const pendingReview = ref<ReviewRead | null>(null)
  const { refreshCount } = useReviewBadge()

  async function refresh() {
    if (!id) return
    isLoading.value = true
    error.value = null
    try {
      campaign.value = await api.get(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this campaign'
    } finally {
      isLoading.value = false
    }
  }

  /** Returns the saved campaign's id (new or existing) so the caller can navigate, or null on
   *  failure. */
  async function save(body: CampaignWrite): Promise<string | null> {
    isSaving.value = true
    saveError.value = null
    skippedDeviceIds.value = []
    try {
      const result = id ? await api.update(id, body) : await api.create(body)
      if (isPendingReview(result)) {
        pendingReview.value = result.pending_review
        void refreshCount()
        return id
      }
      pendingReview.value = null
      campaign.value = result.campaign
      skippedDeviceIds.value = result.skipped_device_ids
      return result.campaign.id
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not save this campaign'
      return null
    } finally {
      isSaving.value = false
    }
  }

  async function remove(): Promise<boolean> {
    if (!id) return false
    isDeleting.value = true
    try {
      const result = await api.remove(id)
      if (isPendingReview(result)) {
        pendingReview.value = result.pending_review
        void refreshCount()
        return false
      }
      return true
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not delete this campaign'
      return false
    } finally {
      isDeleting.value = false
    }
  }

  onMounted(refresh)

  return {
    campaign, isLoading, isSaving, isDeleting, error, saveError, skippedDeviceIds, pendingReview,
    refresh, save, remove,
  }
}
