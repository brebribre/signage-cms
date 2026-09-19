import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useReviewApi } from '@/api/useReviewApi'
import { useReviewBadge } from '@/hooks/useReviews'
import { mediaToDraftElement, readToDraft, websiteToDraftElement } from '@/hooks/usePlaylistEditor'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import type { ElementWrite, ItemWrite, MediaRead, ReviewRead } from '@/types/api'

/**
 * One review, opened: what was sent, shown the way the playlist page shows a playlist, and
 * — for a playlist change — the saved playlist beside it, so "approve" means having seen both.
 * Read-only by construction: nothing here writes back to the draft, only to the review.
 */
export function useReviewDetail(id: string, library: () => MediaRead[]) {
  const api = useReviewApi()
  const playlists = usePlaylistApi()
  const { refreshCount } = useReviewBadge()

  const review = ref<ReviewRead | null>(null)
  const current = ref<DraftItem[] | null>(null)
  const currentName = ref<string | null>(null)
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
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this review'
    } finally {
      isLoading.value = false
    }
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

  return { review, proposed, current, currentName, isLoading, error, isActing, actionError, refresh, approve, reject, withdraw }
}
