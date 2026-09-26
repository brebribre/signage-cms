import { computed, ref } from 'vue'

import { useOperationsApi } from '@/api/useOperationsApi'

/** Until the server has said, the defaults it ships with (backend config: media_max_*_bytes).
 *  The server enforces its own numbers regardless; these only let the browser say no first. */
const MB = 1024 * 1024
const maxImageBytes = ref(25 * MB)
const maxVideoBytes = ref(500 * MB)
let loaded: Promise<void> | null = null

/** A size as people say it: "32 MB", "1.2 GB" — the same wording as the server's refusal. */
export function sizeLabel(bytes: number): string {
  const mb = bytes / MB
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : mb >= 10 ? `${Math.round(mb)} MB` : `${mb.toFixed(1)} MB`
}

/**
 * The biggest single file an upload may be, by kind — from GET /limits, fetched once per page
 * load and shared by every upload area, so changing the backend setting changes what the CMS
 * says and checks without a new build.
 */
export function useUploadLimits() {
  if (!loaded) {
    loaded = useOperationsApi()
      .limits()
      .then((l) => {
        maxImageBytes.value = l.max_image_bytes ?? maxImageBytes.value
        maxVideoBytes.value = l.max_video_bytes ?? maxVideoBytes.value
      })
      .catch(() => {
        loaded = null // try again next time; the defaults stand meanwhile
      })
  }

  /** Why this file can't go up, in a sentence — or null when it can. */
  function tooLarge(file: File, contentType: string): string | null {
    const video = contentType.startsWith('video/')
    const limit = video ? maxVideoBytes.value : maxImageBytes.value
    if (file.size <= limit) return null
    return `${file.name} is ${sizeLabel(file.size)}. ${video ? 'Videos' : 'Pictures'} can be up to ${sizeLabel(limit)}.`
  }

  /** The line under every upload area. */
  const sizeHint = computed(() => `Pictures up to ${sizeLabel(maxImageBytes.value)}, videos up to ${sizeLabel(maxVideoBytes.value)}`)

  return { maxImageBytes, maxVideoBytes, tooLarge, sizeHint }
}
