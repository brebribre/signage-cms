import { ref } from 'vue'

import { ApiError } from '@/api/request'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import type { ItemWrite, PlaylistItemRead } from '@/types/api'

function toItemWrite(item: PlaylistItemRead): ItemWrite {
  return {
    duration_seconds: item.duration_seconds,
    is_enabled: item.is_enabled,
    background: item.background,
    elements: item.elements.map((e) => ({
      media_id: e.media?.id ?? null,
      web_url: e.web_url,
      z_index: e.z_index,
      x: e.x,
      y: e.y,
      width: e.width,
      height: e.height,
      fit: e.fit,
      crop_x: e.crop_x,
      crop_y: e.crop_y,
      crop_zoom: e.crop_zoom,
      has_audio: e.has_audio,
      rotation_degrees: e.rotation_degrees,
    })),
  }
}

/** The quick path into a playlist without the full scene editor: create one from a list of
 *  media, or append media to the end of an existing one. Each media becomes its own full-bleed
 *  scene, with its duration left to the server (a video's own length, else the image default). */
export function usePlaylistCompose() {
  const api = usePlaylistApi()

  const isSaving = ref(false)
  const error = ref<string | null>(null)
  /** A playlist created by an attempt whose item write then failed — reused on retry, so a
   *  flaky second call doesn't leave a trail of empty duplicates behind. */
  let createdId: string | null = null

  async function compose(opts: {
    playlistId: string | null
    name: string
    mediaIds: string[]
  }): Promise<string | null> {
    isSaving.value = true
    error.value = null
    try {
      const existing = opts.playlistId ? (await api.get(opts.playlistId)).items.map(toItemWrite) : []
      const id = opts.playlistId ?? createdId ?? (await api.create(opts.name.trim())).id
      if (!opts.playlistId) createdId = id

      if (opts.mediaIds.length) {
        await api.replaceItems(id, [
          ...existing,
          // Whole media over a blurred background — the same default as adding media in the
          // playlist editor (usePlaylistEditor.addMedia).
          ...opts.mediaIds.map((media_id): ItemWrite => ({
            duration_seconds: null,
            background: 'blur',
            elements: [{ media_id, fit: 'contain' }],
          })),
        ])
      }
      createdId = null
      return id
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not save the playlist'
      return null
    } finally {
      isSaving.value = false
    }
  }

  return { isSaving, error, compose }
}
