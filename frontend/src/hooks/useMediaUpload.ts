import { computed, reactive, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useMediaApi } from '@/api/useMediaApi'
import type { MediaRead } from '@/types/api'

export interface UploadJob {
  id: string
  file: File
  name: string
  status: 'queued' | 'probing' | 'uploading' | 'finishing' | 'done' | 'failed'
  progress: number
  error: string | null
}

/** How long a finished row stays before it removes itself. The file is already visible in
 *  the grid by then, so a lingering "Done" row is just noise. Failures are never
 *  auto-dismissed — those are the ones you need to read. */
const DONE_LINGER_MS = 1500

/** Two at a time. A dozen parallel 200 MB PUTs saturate a venue's uplink and make every
 *  one of them slow, so the queue is the feature, not a limitation. */
const CONCURRENCY = 2

/** Where a video's poster frame is grabbed from. Not 0 — the first frame of a video is
 *  very often black or a fade-in, which makes for a useless thumbnail. */
const POSTER_SECONDS = 1

const THUMB_MAX = 480

interface Probe {
  width: number | null
  height: number | null
  duration: number | null
  thumbnail: Blob | null
}

function drawToJpeg(source: CanvasImageSource, w: number, h: number): Promise<Blob | null> {
  const scale = Math.min(1, THUMB_MAX / Math.max(w, h))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(w * scale)
  canvas.height = Math.round(h * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) return Promise.resolve(null)
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.8))
}

/**
 * Read dimensions, duration and a poster frame from the file itself, in the browser.
 *
 * Deliberate: it keeps `ffmpeg` out of the backend image entirely. Everything here is
 * best-effort — a probe that fails yields nulls and the upload continues, because a video
 * with no thumbnail is still a usable video.
 */
async function probe(file: File): Promise<Probe> {
  const url = URL.createObjectURL(file)
  try {
    if (file.type.startsWith('image/')) {
      const img = new Image()
      await new Promise((res, rej) => {
        img.onload = res
        img.onerror = rej
        img.src = url
      })
      return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        duration: null,
        thumbnail: await drawToJpeg(img, img.naturalWidth, img.naturalHeight),
      }
    }

    const video = document.createElement('video')
    video.muted = true
    video.preload = 'metadata'
    await new Promise((res, rej) => {
      video.onloadedmetadata = res
      video.onerror = rej
      video.src = url
    })
    const duration = Number.isFinite(video.duration) ? video.duration : null
    // Seek before drawing: without this the canvas is blank, because no frame is decoded
    // at metadata time.
    await new Promise((res) => {
      video.onseeked = res
      video.currentTime = Math.min(POSTER_SECONDS, (duration ?? 1) / 2)
      setTimeout(res, 3000) // never hang the queue on a file that will not seek
    })
    return {
      width: video.videoWidth || null,
      height: video.videoHeight || null,
      duration,
      thumbnail: await drawToJpeg(video, video.videoWidth, video.videoHeight),
    }
  } catch {
    return { width: null, height: null, duration: null, thumbnail: null }
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** PUT straight to R2. XHR rather than fetch, because fetch has no upload progress event. */
function put(
  url: string,
  body: Blob,
  contentType: string,
  onProgress?: (fraction: number) => void,
): Promise<string | null> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', url)
    // Must match exactly what was signed, or the signature fails with an error that names
    // nothing useful.
    xhr.setRequestHeader('Content-Type', contentType)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve(xhr.getResponseHeader('ETag'))
        : reject(new Error(`Storage rejected the upload (HTTP ${xhr.status})`))
    xhr.onerror = () =>
      reject(
        new Error(
          'Could not reach storage. If this is the first upload, check the R2 bucket CORS ' +
            'policy allows PUT from this origin.',
        ),
      )
    xhr.send(body)
  })
}

/** Fallback only. See the note on checksums in `runOne`. */
async function sha256(file: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return `sha256:${[...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')}`
}

export function useMediaUpload(onUploaded?: (media: MediaRead) => void) {
  const api = useMediaApi()
  const jobs = ref<UploadJob[]>([])

  const active = computed(() => jobs.value.filter((j) => !['done', 'failed'].includes(j.status)))
  const isUploading = computed(() => active.value.length > 0)

  let running = 0
  const queue: UploadJob[] = []

  async function runOne(job: UploadJob) {
    try {
      job.status = 'probing'
      const info = await probe(job.file)

      job.status = 'uploading'
      const ticket = await api.startUpload({
        filename: job.file.name,
        content_type: job.file.type,
        size_bytes: job.file.size,
      })

      const etag = await put(ticket.upload_url, job.file, job.file.type, (f) => {
        job.progress = f
      })

      if (info.thumbnail) {
        await put(ticket.thumbnail_upload_url, info.thumbnail, 'image/jpeg')
      }

      job.status = 'finishing'
      // The checksum is the content's identity — the Android player caches by it, so a
      // re-issued URL for unchanged content is not a re-download.
      //
      // Taken from R2's ETag rather than hashed here. Hashing client-side means
      // `crypto.subtle.digest`, which needs the *whole* file in memory at once and has no
      // streaming form: a 500 MB video would freeze the tab and risk an allocation failure.
      // The ETag is computed server-side for free and is stable for the object's lifetime,
      // which is all a cache key needs. It requires `ExposeHeaders: ["ETag"]` in the bucket
      // CORS policy; if that is missing we fall back to hashing, which works but is slow.
      const checksum = etag ? `md5:${etag.replaceAll('"', '')}` : await sha256(job.file)

      const media = await api.complete(ticket.media_id, {
        checksum,
        width: info.width,
        height: info.height,
        duration_seconds: info.duration,
      })

      job.status = 'done'
      job.progress = 1
      onUploaded?.(media)
      setTimeout(() => dismiss(job.id), DONE_LINGER_MS)
    } catch (e) {
      job.status = 'failed'
      job.error = e instanceof ApiError || e instanceof Error ? e.message : 'Upload failed'
    } finally {
      running--
      pump()
    }
  }

  function pump() {
    while (running < CONCURRENCY && queue.length) {
      const job = queue.shift()!
      running++
      void runOne(job)
    }
  }

  function add(files: File[] | FileList) {
    for (const file of Array.from(files)) {
      // `reactive`, not a plain object. Pushing a raw object into `jobs` and then mutating
      // that same raw reference from `runOne` writes straight past the reactive proxy, so
      // nothing is notified: the computed `isUploading` stays cached at true and the row
      // sits on "Uploading…" forever even though the job finished.
      const job = reactive<UploadJob>({
        id: crypto.randomUUID(),
        file,
        name: file.name,
        status: 'queued',
        progress: 0,
        error: null,
      })
      jobs.value.push(job)
      queue.push(job)
    }
    pump()
  }

  function dismiss(id: string) {
    jobs.value = jobs.value.filter((j) => j.id !== id)
  }

  function clearFinished() {
    jobs.value = jobs.value.filter((j) => j.status !== 'done' && j.status !== 'failed')
  }

  return { jobs, active, isUploading, add, dismiss, clearFinished }
}
