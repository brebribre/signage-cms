import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import type { ElementRead, ItemFit, MediaRead, PlaylistDetail, PlaylistItemRead } from '@/types/api'

/** One media element within a scene, positioned/sized/rotated on its own. Mirrors
 *  ElementRead but is local until Save. */
export interface DraftElement {
  key: string
  mediaId: string
  filename: string
  kind: 'image' | 'video'
  thumbnailUrl: string | null
  url: string
  mediaWidth: number | null
  mediaHeight: number | null
  mediaDuration: number | null
  zIndex: number
  x: number
  y: number
  width: number
  height: number
  fit: ItemFit
  cropX: number | null
  cropY: number | null
  cropZoom: number | null
  hasAudio: boolean
  rotationDegrees: number
}

/** One slot (scene) being edited. Mirrors PlaylistItemRead but is local until Save. */
export interface DraftItem {
  key: string
  durationSeconds: number
  isEnabled: boolean
  elements: DraftElement[]
}

const IMAGE_DEFAULT_SECONDS = 10

/** A fresh element for `media`, full-bleed by default — the common case (one element filling
 *  the whole scene) is just this with no overrides. `SceneEditor.vue` calls this too, with a
 *  smaller centered default, when adding an element into an already-populated scene, so the
 *  two paths can never drift on what a "new element" starts out as. */
export function mediaToDraftElement(m: MediaRead, overrides: Partial<DraftElement> = {}): DraftElement {
  return {
    key: crypto.randomUUID(),
    mediaId: m.id,
    filename: m.filename,
    kind: m.kind,
    thumbnailUrl: m.thumbnail_url,
    url: m.url,
    mediaWidth: m.width,
    mediaHeight: m.height,
    mediaDuration: m.duration_seconds,
    zIndex: 0,
    x: 0,
    y: 0,
    width: 1,
    height: 1,
    fit: 'cover',
    cropX: null,
    cropY: null,
    cropZoom: null,
    hasAudio: false,
    rotationDegrees: 0,
    ...overrides,
  }
}

/** A fresh, empty scene — the "Create custom" starting point. Callers push this into
 *  `draft` themselves (typically only once the canvas editor's first Apply gives it
 *  elements), so cancelling out of the editor never leaves a stray empty scene behind. */
export function createEmptyItem(): DraftItem {
  return { key: crypto.randomUUID(), durationSeconds: IMAGE_DEFAULT_SECONDS, isEnabled: true, elements: [] }
}

function toDraftElement(el: ElementRead): DraftElement {
  return {
    key: el.id,
    mediaId: el.media.id,
    filename: el.media.filename,
    kind: el.media.kind,
    thumbnailUrl: el.media.thumbnail_url,
    url: el.media.url,
    mediaWidth: el.media.width,
    mediaHeight: el.media.height,
    mediaDuration: el.media.duration_seconds,
    zIndex: el.z_index,
    x: el.x,
    y: el.y,
    width: el.width,
    height: el.height,
    fit: el.fit,
    cropX: el.crop_x,
    cropY: el.crop_y,
    cropZoom: el.crop_zoom,
    hasAudio: el.has_audio,
    rotationDegrees: el.rotation_degrees,
  }
}

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
        d.durationSeconds, d.isEnabled,
        d.elements.map((e) => [
          e.mediaId, e.zIndex, e.x, e.y, e.width, e.height, e.fit,
          e.cropX, e.cropY, e.cropZoom, e.hasAudio, e.rotationDegrees,
        ]),
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
      durationSeconds: item.duration_seconds,
      isEnabled: item.is_enabled,
      elements: item.elements.map(toDraftElement),
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

  /** Each picked media becomes its own new scene (slot), one full-bleed element — "Add
   *  media" on the playlist row list, not "add an element to this scene" (that's
   *  SceneEditor.vue, mutating one scene's `elements` array directly). */
  function addMedia(media: MediaRead[]) {
    for (const m of media) {
      draft.value.push({
        key: crypto.randomUUID(),
        durationSeconds:
          m.kind === 'video' && m.duration_seconds
            ? Math.max(1, Math.round(m.duration_seconds))
            : IMAGE_DEFAULT_SECONDS,
        isEnabled: true,
        elements: [mediaToDraftElement(m)],
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
            duration_seconds: d.durationSeconds,
            is_enabled: d.isEnabled,
            elements: d.elements.map((e) => ({
              media_id: e.mediaId,
              z_index: e.zIndex,
              x: e.x,
              y: e.y,
              width: e.width,
              height: e.height,
              fit: e.fit,
              crop_x: e.cropX,
              crop_y: e.cropY,
              crop_zoom: e.cropZoom,
              has_audio: e.hasAudio,
              rotation_degrees: e.rotationDegrees,
            })),
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
