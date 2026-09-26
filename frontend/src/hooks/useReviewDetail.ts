import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useCampaignApi } from '@/api/useCampaignApi'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useReviewApi } from '@/api/useReviewApi'
import { useReviewBadge } from '@/hooks/useReviews'
import { mediaToDraftElement, readToDraft, textToDraftElement, websiteToDraftElement } from '@/hooks/usePlaylistEditor'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import type { CampaignRuleWrite, ElementWrite, ItemWrite, MediaRead, ReviewRead } from '@/types/api'

/** A campaign as a review shows it — the saved one (Before) or the one sent (After). */
export interface CampaignSide {
  name: string
  device_ids: string[]
  rules: CampaignRuleWrite[]
}

/** A playlist a campaign's rules put on screens, loaded so its scenes can be previewed. Null
 *  scenes: it could not be loaded — most likely deleted since the review was sent. */
export interface RulePlaylist {
  name: string | null
  scenes: DraftItem[] | null
}

const CAMPAIGN_KINDS = new Set(['campaign_create', 'campaign_update', 'campaign_delete'])

/**
 * One review, opened: what was sent, shown the way the playlist page shows a playlist, and
 * — for a playlist change — the saved playlist beside it, so "approve" means having seen both.
 * Read-only by construction: nothing here writes back to the draft, only to the review.
 */
export function useReviewDetail(id: string, library: () => MediaRead[]) {
  const api = useReviewApi()
  const playlists = usePlaylistApi()
  const campaigns = useCampaignApi()
  const { refreshCount } = useReviewBadge()

  const review = ref<ReviewRead | null>(null)
  const current = ref<DraftItem[] | null>(null)
  const currentName = ref<string | null>(null)
  /** A campaign change: the campaign as saved now. Null for a new one, or one deleted since. */
  const campaignBefore = ref<CampaignSide | null>(null)
  /** Every playlist either side of a campaign change plays, by id. */
  const rulePlaylists = ref<Map<string, RulePlaylist>>(new Map())
  const isLoading = ref(true)
  const error = ref<string | null>(null)
  const isActing = ref(false)
  const actionError = ref<string | null>(null)

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      review.value = await api.get(id)
      if (review.value.kind === 'playlist_items' && review.value.target_id) {
        // The saved playlist, for the Current side of the preview. Its absence (deleted since)
        // is a fact the page shows, not a failure.
        try {
          const saved = await playlists.get(review.value.target_id)
          current.value = saved.items.map(readToDraft)
          currentName.value = saved.name
        } catch {
          current.value = null
        }
      }
      if (CAMPAIGN_KINDS.has(review.value.kind)) await loadCampaign(review.value)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this review'
    } finally {
      isLoading.value = false
    }
  }

  /** A campaign change as sent. Null for a removal, which sends nothing but the campaign's id. */
  const campaignAfter = computed<CampaignSide | null>(() => {
    const r = review.value
    if (!r || (r.kind !== 'campaign_create' && r.kind !== 'campaign_update')) return null
    const p = r.payload as Partial<CampaignSide>
    return { name: p.name ?? r.target_name, device_ids: p.device_ids ?? [], rules: p.rules ?? [] }
  })

  /** The saved campaign, and the scenes of every playlist on either side, fetched together so
   *  the preview can switch rules without a wait. A playlist that fails to load is kept as a
   *  gap the page names, not a failure of the whole review. */
  async function loadCampaign(r: ReviewRead) {
    if (r.kind !== 'campaign_create' && r.target_id) {
      try {
        const saved = await campaigns.get(r.target_id)
        campaignBefore.value = { name: saved.name, device_ids: saved.device_ids, rules: saved.rules }
      } catch {
        campaignBefore.value = null
      }
    }
    const ids = new Set([
      ...(campaignBefore.value?.rules ?? []).map((x) => x.playlist_id),
      ...(campaignAfter.value?.rules ?? []).map((x) => x.playlist_id),
    ])
    const loaded = await Promise.all(
      [...ids].map(async (pid): Promise<[string, RulePlaylist]> => {
        try {
          const detail = await playlists.get(pid)
          return [pid, { name: detail.name, scenes: detail.items.map(readToDraft) }]
        } catch {
          return [pid, { name: null, scenes: null }]
        }
      }),
    )
    rulePlaylists.value = new Map(loaded)
  }

  /** The proposed scenes as DraftItems, built from the stored request plus the media library —
   *  the same shape the playlist page previews, so the same components draw it. A file that has
   *  since left the library shows as a blank element rather than breaking the preview. */
  const proposed = computed<DraftItem[]>(() => {
    const r = review.value
    if (!r || r.kind !== 'playlist_items') return []
    const items = (r.payload.items as ItemWrite[] | undefined) ?? []
    const byId = new Map(library().map((m) => [m.id, m]))
    return items.map((item, i) => ({
      key: `proposed-${i}`,
      durationSeconds: item.duration_seconds ?? 10,
      isEnabled: item.is_enabled ?? true,
      background: item.background ?? 'black',
      backgroundColor: item.background_color ?? null,
      elements: item.elements.map((el, j) => toDraft(el, byId, `proposed-${i}-${j}`)),
    }))
  })

  function toDraft(el: ElementWrite, byId: Map<string, MediaRead>, key: string) {
    const placement = {
      key,
      zIndex: el.z_index ?? 0,
      x: el.x ?? 0, y: el.y ?? 0, width: el.width ?? 1, height: el.height ?? 1,
      fit: el.fit ?? 'cover',
      cropX: el.crop_x ?? null, cropY: el.crop_y ?? null, cropZoom: el.crop_zoom ?? null,
      hasAudio: el.has_audio ?? false,
      rotationDegrees: el.rotation_degrees ?? 0,
    }
    if (el.text != null) return textToDraftElement(el.text, el.text_style ?? undefined, placement)
    if (el.web_url) return websiteToDraftElement(el.web_url, placement)
    const media = el.media_id ? byId.get(el.media_id) : undefined
    if (media) return mediaToDraftElement(media, placement)
    return { ...websiteToDraftElement('', placement), kind: 'image' as const, filename: 'Missing file', url: '' }
  }

  async function act(fn: () => Promise<ReviewRead>): Promise<boolean> {
    isActing.value = true
    actionError.value = null
    try {
      review.value = await fn()
      void refreshCount()
      return true
    } catch (e) {
      actionError.value = e instanceof ApiError ? e.message : 'Could not update this review'
      return false
    } finally {
      isActing.value = false
    }
  }

  const approve = (note?: string) => act(() => api.approve(id, note))
  const reject = (note?: string) => act(() => api.reject(id, note))
  const withdraw = () => act(() => api.withdraw(id))

  onMounted(refresh)

  return { review, proposed, current, currentName, campaignBefore, campaignAfter, rulePlaylists, isLoading, error, isActing, actionError, refresh, approve, reject, withdraw }
}
