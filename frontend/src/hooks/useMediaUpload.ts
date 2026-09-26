import { mediaContentType } from '@/utils/mediaTypes'
import { computed, reactive, ref } from 'vue'

import { ApiError } from '@/api/request'
import { useMediaApi } from '@/api/useMediaApi'
import type { MediaRead } from '@/types/api'
import { useUploadLimits } from '@/hooks/useUploadLimits'

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
const DONE_LINGER_MS = 1200

/** Two at a time. A dozen parallel 200 MB PUTs saturate a venue's uplink and make every
 *  one of them slow, so the queue is the feature, not a limitation. */
const CONCURRENCY = 2

/** Where a video's poster frame is grabbed from, tried in turn until one isn't black: a
 *  second in (the first frame is very often black or a fade-in), then a quarter and half way
 *  through, for a video that opens dark. Fractions are of the duration. */
const POSTER_SECONDS = 1
const POSTER_FRACTIONS = [0.25, 0.5]

/** A frame whose average brightness (0–255) is below this is treated as black. Matches the
 *  server's check (services/video_streams.py::DARK_MEAN). */
const DARK_MEAN = 8

const THUMB_MAX = 480

interface Probe {
  width: number | null
  height: number | null
  duration: number | null
  thumbnail: Blob | null
}

function drawToCanvas(source: CanvasImageSource, w: number, h: number): HTMLCanvasElement | null {
  const scale = Math.min(1, THUMB_MAX / Math.max(w, h))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(w * scale))
  canvas.height = Math.max(1, Math.round(h * scale))
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  return canvas
}

function toJpeg(canvas: HTMLCanvasElement | null): Promise<Blob | null> {
  return canvas ? new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.8)) : Promise.resolve(null)
}

function drawToJpeg(source: CanvasImageSource, w: number, h: number): Promise<Blob | null> {
  return toJpeg(drawToCanvas(source, w, h))
}

/** Average brightness of what was drawn, from a sparse sample of pixels — enough to tell a real
 *  frame from the black one a browser draws when it hasn't decoded anything yet. */
function isDark(canvas: HTMLCanvasElement): boolean {
  const ctx = canvas.getContext('2d')
  if (!ctx) return true
  let data: Uint8ClampedArray
  try {
    data = ctx.getImageData(0, 0, canvas.width, canvas.height).data
  } catch {
    return false // unreadable (shouldn't happen for a local file): don't throw a frame away over it
  }
  let sum = 0
  let n = 0
  for (let i = 0; i < data.length; i += 4 * 16) {
    sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    n++
  }
  return n === 0 || sum / n < DARK_MEAN
}

/** Move to a time and wait until a frame there is actually decoded — not just "seeked", which
 *  Safari reports before the picture is ready (drawing then gives a black frame). False when
 *  the video never got there. */
async function seekTo(video: HTMLVideoElement, seconds: number): Promise<boolean> {
  const arrived = await new Promise<boolean>((res) => {
    const timer = setTimeout(() => res(false), 3000) // never hang the queue on a file that will not seek
    video.onseeked = () => {
      clearTimeout(timer)
      res(true)
    }
    video.currentTime = seconds
  })
  if (!arrived) return false
  // Wait for the frame itself: requestVideoFrameCallback where there is one, else until the
  // element says it holds current data, then one more paint for good measure.
  const rvfc = (video as HTMLVideoElement & { requestVideoFrameCallback?: (cb: () => void) => number })
    .requestVideoFrameCallback
  await new Promise<void>((res) => {
    const timer = setTimeout(res, 500)
    const done = () => {
      clearTimeout(timer)
      res()
    }
    if (rvfc) rvfc.call(video, done)
    else if (video.readyState >= 2) done()
    else video.onloadeddata = done
  })
  await new Promise((res) => requestAnimationFrame(() => res(null)))
  return video.readyState >= 2
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
    if (mediaContentType(file).startsWith('image/')) {
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
    // iPhone Safari decodes nothing for a video that isn't allowed to play inline, and with only
    // metadata loaded — so every frame it draws is black. Inline, and allowed to load data.
    video.playsInline = true
    video.setAttribute('playsinline', '')
    video.preload = 'auto'
    await new Promise((res, rej) => {
      video.onloadedmetadata = res
      video.onerror = rej
      video.src = url
    })
    const duration = Number.isFinite(video.duration) ? video.duration : null
    const w = video.videoWidth
    const h = video.videoHeight

    // A few points in, until one draws as a real picture. None does — the browser can't decode
    // this file (an H.265 .mov in Chrome), or the video is dark there — and no thumbnail is
    // sent: the server makes one from the playback copy, which it can always read.
    let thumbnail: Blob | null = null
    const points = [Math.min(POSTER_SECONDS, (duration ?? 1) / 2), ...POSTER_FRACTIONS.map((f) => (duration ?? 0) * f)]
    for (const t of [...new Set(points.map((p) => Math.round(p * 100) / 100))]) {
      if (!w || !h || !(await seekTo(video, t))) break
      const canvas = drawToCanvas(video, w, h)
      if (canvas && !isDark(canvas)) {
        thumbnail = await toJpeg(canvas)
        break
      }
    }
    return { width: w || null, height: h || null, duration, thumbnail }
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
      const contentType = mediaContentType(job.file)
      const ticket = await api.startUpload({
        filename: job.file.name,
        content_type: contentType,
        size_bytes: job.file.size,
      })

      // The thumbnail goes up alongside the file rather than after it: waiting for it once the
      // file's bar was already full was a pause with nothing on screen to explain it. It's small,
      // so it barely competes for the uplink.
      const thumbnailPut = info.thumbnail
        ? put(ticket.thumbnail_upload_url, info.thumbnail, 'image/jpeg')
        : Promise.resolve(null)
      const [etag] = await Promise.all([
        put(ticket.upload_url, job.file, contentType, (f) => {
          job.progress = f
        }),
        thumbnailPut,
      ])

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

  const { tooLarge } = useUploadLimits()

  function add(files: File[] | FileList) {
    for (const file of Array.from(files)) {
      // Too big is said here, on the file's own row, before a byte moves — the rest still go.
      const refused = tooLarge(file, mediaContentType(file))
      // `reactive`, not a plain object. Pushing a raw object into `jobs` and then mutating
      // that same raw reference from `runOne` writes straight past the reactive proxy, so
      // nothing is notified: the computed `isUploading` stays cached at true and the row
      // sits on "Uploading…" forever even though the job finished.
      const job = reactive<UploadJob>({
        id: crypto.randomUUID(),
        file,
        name: file.name,
        status: refused ? 'failed' : 'queued',
        progress: 0,
        error: refused,
      })
      jobs.value.push(job)
      if (!refused) queue.push(job)
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
