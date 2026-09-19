import { computed, onMounted, ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useReviewBadge } from '@/hooks/useReviews'
import type { ElementRead, ItemFit, MediaRead, PlaylistDetail, PlaylistItemRead, ReviewRead, SceneBackground, TextStyle } from '@/types/api'
import { TEXT_DEFAULT_STYLE, textLabel } from '@/utils/textStyle'
import { isPendingReview } from '@/types/api'
import { websiteLabel } from '@/utils/websiteUrl'

/** One element within a scene — a library file or a live website — positioned/sized/rotated
 *  on its own. Mirrors ElementRead but is local until Save. */
export interface DraftElement {
  key: string
  /** Null for a website element. */
  mediaId: string | null
  /** A website shown live, set instead of `mediaId`. `url` holds the same address. */
  webUrl: string | null
  /** Text drawn by the player, set instead of both. `textStyle` is always set with it. */
  text: string | null
  textStyle: TextStyle | null
  filename: string
  kind: 'image' | 'video' | 'web' | 'text'
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
  background: SceneBackground
  elements: DraftElement[]
}

/** Videos and websites are a scene's "live" elements, and they are what a screen runs out of:
 *  a video holds a hardware decoder and its own surface, a website its own renderer process.
 *  A TV box handles two of them in one scene; three is where it crashes. Images don't count.
 *  The same numbers as the server's (services/playlists.py MAX_LIVE_ELEMENTS and
 *  MAX_VIDEO_ELEMENTS), which rejects a scene over them — the editor just says so first. */
export const MAX_LIVE_ELEMENTS = 2
export const MAX_VIDEO_ELEMENTS = 1

export function isLiveKind(kind: DraftElement['kind']): boolean {
  return kind === 'video' || kind === 'web'
}

export interface LiveBudget {
  live: number
  videos: number
  /** No more videos or websites fit. */
  liveFull: boolean
  /** No more videos fit (a website still may). */
  videoFull: boolean
  /** Past a limit — only possible for a scene saved before the limits existed. */
  over: boolean
}

export function liveBudget(elements: Pick<DraftElement, 'kind'>[]): LiveBudget {
  const live = elements.filter((e) => isLiveKind(e.kind)).length
  const videos = elements.filter((e) => e.kind === 'video').length
  return {
    live,
    videos,
    liveFull: live >= MAX_LIVE_ELEMENTS,
    videoFull: videos >= MAX_VIDEO_ELEMENTS,
    over: live > MAX_LIVE_ELEMENTS || videos > MAX_VIDEO_ELEMENTS,
  }
}

/** Why an element of `kind` can't join the scene right now, in the user's words — or null. */
export function liveBlockReason(budget: LiveBudget, kind: DraftElement['kind']): string | null {
  if (!isLiveKind(kind)) return null
  if (kind === 'video' && budget.videoFull) return 'A scene can only have one video.'
  if (budget.liveFull) {
    return `A scene can only have ${MAX_LIVE_ELEMENTS} live elements (videos or websites). Remove one to add another.`
  }
  return null
}

const IMAGE_DEFAULT_SECONDS = 10
/** Same as the server's default for a website scene: it takes a moment to load, and is
 *  usually worth reading. */
const WEB_DEFAULT_SECONDS = 30

/** A fresh element for `media`, full-bleed by default — the common case (one element filling
 *  the whole scene) is just this with no overrides. `SceneEditor.vue` calls this too, with a
 *  smaller centered default, when adding an element into an already-populated scene, so the
 *  two paths can never drift on what a "new element" starts out as. */
export function mediaToDraftElement(m: MediaRead, overrides: Partial<DraftElement> = {}): DraftElement {
  return {
    key: crypto.randomUUID(),
    mediaId: m.id,
    webUrl: null,
    text: null,
    textStyle: null,
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

/** A fresh website element, full-bleed by default — the website counterpart of
 *  `mediaToDraftElement`. It has no intrinsic size, so nothing to crop, rotate or unmute. */
export function websiteToDraftElement(url: string, overrides: Partial<DraftElement> = {}): DraftElement {
  return {
    key: crypto.randomUUID(),
    mediaId: null,
    webUrl: url,
    text: null,
    textStyle: null,
    filename: websiteLabel(url),
    kind: 'web',
    thumbnailUrl: null,
    url,
    mediaWidth: null,
    mediaHeight: null,
    mediaDuration: null,
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
  return {
    key: crypto.randomUUID(), durationSeconds: IMAGE_DEFAULT_SECONDS, isEnabled: true, background: 'black', elements: [],
  }
}

function toDraftElement(el: ElementRead): DraftElement {
  const placement = {
    key: el.id,
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
  if (el.text != null) return textToDraftElement(el.text, el.text_style ?? undefined, placement)
  if (!el.media) return websiteToDraftElement(el.web_url ?? '', placement)
  return {
    ...placement,
    mediaId: el.media.id,
    webUrl: null,
    text: null,
    textStyle: null,
    filename: el.media.filename,
    kind: el.media.kind,
    thumbnailUrl: el.media.thumbnail_url,
    url: el.media.url,
    mediaWidth: el.media.width,
    mediaHeight: el.media.height,
    mediaDuration: el.media.duration_seconds,
  }
}

/** A fresh text element — the third kind, after a file and a website. Its box is whatever the
 *  caller says; a new one from the scene editor starts centred and a few lines tall. */
export function textToDraftElement(text: string, style: Partial<TextStyle> = {}, overrides: Partial<DraftElement> = {}): DraftElement {
  const textStyle = { ...TEXT_DEFAULT_STYLE, ...style }
  return {
    key: crypto.randomUUID(),
    mediaId: null,
    webUrl: null,
    text,
    textStyle,
    filename: textLabel(text),
    kind: 'text',
    thumbnailUrl: null,
    url: '',
    mediaWidth: null,
    mediaHeight: null,
    mediaDuration: null,
    zIndex: 0,
    x: 0.2,
    y: 0.4,
    width: 0.6,
    height: 0.2,
    fit: 'cover',
    cropX: null,
    cropY: null,
    cropZoom: null,
    hasAudio: false,
    rotationDegrees: 0,
    ...overrides,
  }
}

/** A saved scene as the editor and the preview hold it. Exported for the review page, which
 *  previews a saved playlist next to a proposed one through the same components. */
export function readToDraft(item: PlaylistItemRead): DraftItem {
  return {
    key: item.id,
    durationSeconds: item.duration_seconds,
    isEnabled: item.is_enabled,
    background: item.background ?? 'black',
    elements: item.elements.map(toDraftElement),
  }
}

export function usePlaylistEditor(id: string) {
  const api = usePlaylistApi()

  const playlist = ref<PlaylistDetail | null>(null)
  const draft = ref<DraftItem[]>([])
  /** The name as edited, saved with everything else by Save. */
  const draftName = ref('')
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const saveError = ref<string | null>(null)
  const deleteError = ref<string | null>(null)

  /** Compared against the loaded playlist so Save can be disabled when nothing changed —
   *  and so leaving with unsaved work can be warned about. */
  /** Set when the last save was parked for the owner instead of applied (a manager saving a
   *  playlist that is on screens). The draft is kept as sent, so the page can keep showing
   *  it, but the saved playlist itself has not changed. */
  const pendingReview = ref<ReviewRead | null>(null)
  const { refreshCount } = useReviewBadge()

  const savedSnapshot = ref('')
  const snapshot = computed(() =>
    JSON.stringify(
      draft.value.map((d) => [
        d.durationSeconds, d.isEnabled, d.background,
        d.elements.map((e) => [
          e.mediaId, e.webUrl, e.zIndex, e.x, e.y, e.width, e.height, e.fit,
          e.cropX, e.cropY, e.cropZoom, e.hasAudio, e.rotationDegrees,
        ]),
      ]),
    ),
  )
  const itemsDirty = computed(() => snapshot.value !== savedSnapshot.value)
  const nameDirty = computed(() => !!playlist.value && draftName.value.trim() !== playlist.value.name)
  const isDirty = computed(() => itemsDirty.value || nameDirty.value)

  const totalSeconds = computed(() =>
    draft.value.filter((d) => d.isEnabled).reduce((sum, d) => sum + d.durationSeconds, 0),
  )
  const enabledCount = computed(() => draft.value.filter((d) => d.isEnabled).length)

  const toDraft = readToDraft

  function adopt(detail: PlaylistDetail) {
    playlist.value = detail
    draft.value = detail.items.map(toDraft)
    draftName.value = detail.name
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
        // Whole media, never cropped, with a blurred copy filling the rest of the screen: the
        // playlist may run on portrait and landscape screens alike, and this looks right on
        // both without anyone arranging it. Placement by hand is the scene editor's job.
        isEnabled: true,
        background: 'blur',
        elements: [mediaToDraftElement(m, { fit: 'contain' })],
      })
    }
  }

  /** A website as its own new scene, full-bleed — `addMedia`'s counterpart. `url` must already
   *  be a normalized https address (see utils/websiteUrl.ts). */
  function addWebsite(url: string) {
    draft.value.push({
      key: crypto.randomUUID(),
      durationSeconds: WEB_DEFAULT_SECONDS,
      isEnabled: true,
      background: 'black',
      elements: [websiteToDraftElement(url)],
    })
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
      if (!draftName.value.trim()) draftName.value = playlist.value?.name ?? ''
      if (nameDirty.value) {
        const updated = await api.update(id, { name: draftName.value.trim() })
        // A rename alone is never parked, so this is always the playlist.
        if (!isPendingReview(updated)) {
          // Recorded now, so a failure saving the scenes below doesn't send the name again.
          if (playlist.value) playlist.value.name = updated.name
          draftName.value = updated.name
        }
      }
      // Scenes are only sent when they changed: sending them again would reload every screen.
      if (!itemsDirty.value) return true
      const result = await api.replaceItems(
          id,
          draft.value.map((d) => ({
            duration_seconds: d.durationSeconds,
            is_enabled: d.isEnabled,
            background: d.background,
            elements: d.elements.map((e) => ({
              media_id: e.mediaId,
              web_url: e.webUrl,
              text: e.text,
              text_style: e.text != null ? e.textStyle ?? TEXT_DEFAULT_STYLE : null,
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
        )
      if (isPendingReview(result)) {
        // Parked, not saved: keep the draft on the page, treat it as clean so leaving is not a
        // "discard changes?" fight, and let the owner's badge know.
        pendingReview.value = result.pending_review
        savedSnapshot.value = snapshot.value
        void refreshCount()
        return true
      }
      pendingReview.value = null
      adopt(result)
      return true
    } catch (e) {
      saveError.value = e instanceof ApiError ? e.message : 'Could not save'
      return false
    } finally {
      isSaving.value = false
    }
  }

  async function setShuffle(shuffle: boolean) {
    try {
      const updated = await api.update(id, { shuffle })
      if (isPendingReview(updated)) {
        pendingReview.value = updated.pending_review
        void refreshCount()
        return
      }
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
    playlist, draft, draftName, isLoading, isSaving, isDirty, error, saveError, deleteError,
    pendingReview, totalSeconds, enabledCount,
    addMedia, addWebsite, removeAt, move, save, setShuffle, remove, refresh,
  }
}
