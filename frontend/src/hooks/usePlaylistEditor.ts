import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import type { ItemFit, MediaRead, PlaylistDetail, PlaylistItemRead } from '@/types/api'

/** A row being edited. Mirrors PlaylistItemRead but is local until Save. */
export interface DraftItem {
  key: string
  mediaId: string
  filename: string
  kind: 'image' | 'video'
  thumbnailUrl: string | null
  url: string
  mediaWidth: number | null
  mediaHeight: number | null
  mediaDuration: number | null
  durationSeconds: number
  fit: ItemFit
  isEnabled: boolean
  cropX: number | null
  cropY: number | null
  cropZoom: number | null
  hasAudio: boolean
}

const IMAGE_DEFAULT_SECONDS = 10

export function usePlaylistEditor(id: string) {
  const api = usePlaylistApi()

  const playlist = ref<PlaylistDetail | null>(null)
  const draft = ref<DraftItem[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  const deleteError = ref<string | null>(null)

  /** Compared against the loaded playlist so Save can be disabled when nothing changed —
   *  and so leaving with unsaved work can be warned about. */
  const savedSnapshot = ref('')
  const snapshot = computed(() =>
    JSON.stringify(
      draft.value.map((d) => [
        d.mediaId, d.durationSeconds, d.fit, d.isEnabled,
        d.cropX, d.cropY, d.cropZoom, d.hasAudio,
      ]),
    ),
  )
  const isDirty = computed(() => snapshot.value !== savedSnapshot.value)

  const totalSeconds = computed(() =>
    draft.value.filter((d) => d.isEnabled).reduce((sum, d) => sum + d.durationSeconds, 0),
  )
  const enabledCount = computed(() => draft.value.filter((d) => d.isEnabled).length)

  function toDraft(item: PlaylistItemRead): DraftItem {
    return {
      key: item.id,
      mediaId: item.media.id,
      filename: item.media.filename,
      kind: item.media.kind,
      thumbnailUrl: item.media.thumbnail_url,
      url: item.media.url,
      mediaWidth: item.media.width,
      mediaHeight: item.media.height,
      mediaDuration: item.media.duration_seconds,
      durationSeconds: item.duration_seconds,
      fit: item.fit,
      isEnabled: item.is_enabled,
      cropX: item.crop_x,
      cropY: item.crop_y,
      cropZoom: item.crop_zoom,
      hasAudio: item.has_audio,
    }
  }

  function adopt(detail: PlaylistDetail) {
    playlist.value = detail
    draft.value = detail.items.map(toDraft)
    savedSnapshot.value = snapshot.value
  }

  async function refresh() {
    isLoading.value = true
    error.value = null
    try {
      adopt(await api.get(id))
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this playlist'
    } finally {
      isLoading.value = false
    }
  }

  function addMedia(media: MediaRead[]) {
    for (const m of media) {
      draft.value.push({
        // Not the media id: the same file may legitimately appear twice in one loop.
        key: crypto.randomUUID(),
        mediaId: m.id,
        filename: m.filename,
        kind: m.kind,
        thumbnailUrl: m.thumbnail_url,
        url: m.url,
        mediaWidth: m.width,
        mediaHeight: m.height,
        mediaDuration: m.duration_seconds,
        durationSeconds:
          m.kind === 'video' && m.duration_seconds
            ? Math.max(1, Math.round(m.duration_seconds))
            : IMAGE_DEFAULT_SECONDS,
        fit: 'contain',
        isEnabled: true,
        cropX: null,
        cropY: null,
        cropZoom: null,
        hasAudio: false,
      })
    }
  }

  function removeAt(index: number) {
    draft.value.splice(index, 1)
  }

  /** Reorder by index. The array *is* the order — position is never stored client-side. */
  function move(from: number, to: number) {
    if (from === to || to < 0 || to >= draft.value.length) return
    const [row] = draft.value.splice(from, 1)
    draft.value.splice(to, 0, row)
  }

  async function save(): Promise<boolean> {
    isSaving.value = true
    saveError.value = null
    try {
      adopt(
        await api.replaceItems(
          id,
          draft.value.map((d) => ({
            media_id: d.mediaId,
            duration_seconds: d.durationSeconds,
            fit: d.fit,
            is_enabled: d.isEnabled,
            crop_x: d.cropX,
            crop_y: d.cropY,
            crop_zoom: d.cropZoom,
            has_audio: d.hasAudio,
          })),
        ),
      )
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not save'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function rename(name: string) {
    if (!name.trim() || name === playlist.value?.name) return
    try {
      const updated = await api.update(id, { name })
      if (playlist.value) playlist.value.name = updated.name
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not rename'
    }
  }

  async function setShuffle(shuffle: boolean) {
    try {
      const updated = await api.update(id, { shuffle })
      if (playlist.value) playlist.value.shuffle = updated.shuffle
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not update'
    }
  }

  async function remove(): Promise<boolean> {
    deleteError.value = null
    try {
      await api.remove(id)
      return true
    } catch (e) {
      // A 409 already names the screens — show it as it came.
      deleteError.value = e instanceof ApiError ? e.message : 'Could not delete'
      return false
    }
  }

  onMounted(refresh)

  return {
    playlist, draft, isLoading, isSaving, isDirty, error, saveError, deleteError,
    totalSeconds, enabledCount,
    addMedia, removeAt, move, save, rename, setShuffle, remove, refresh,
  }
}
