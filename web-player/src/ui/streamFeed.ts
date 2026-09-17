/**
 * Plays a stored streaming copy (fragmented MP4, see `storedFile` in engine.ts) through Media
 * Source Extensions.
 *
 * Why not just `video.src = blobUrl`: a smart TV's browser hands a plain video to the TV's own
 * media player, which can't open a file that lives inside the browser — a black screen. With
 * MediaSource the page itself hands the browser the bytes, which is the path TV browsers support
 * (it's how YouTube and Netflix play on them).
 *
 * The file is read a fragment at a time straight from the stored blob — never loaded whole — and
 * appended only while less than [BUFFER_AHEAD_SECONDS] is buffered ahead, so a long video never
 * outgrows a TV's small media buffer. Played ranges are dropped if the buffer fills anyway.
 */

/** How much to keep buffered ahead of the play position. */
const BUFFER_AHEAD_SECONDS = 30
/** How much already-played video to keep when the buffer is full. */
const KEEP_BEHIND_SECONDS = 5

interface Box {
  type: string
  start: number
  end: number
}

/** The file's top-level MP4 boxes, read header by header from the blob. */
async function topLevelBoxes(blob: Blob): Promise<Box[]> {
  const boxes: Box[] = []
  let offset = 0
  while (offset + 8 <= blob.size) {
    const view = new DataView(await blob.slice(offset, offset + 16).arrayBuffer())
    let size = view.getUint32(0)
    const type = String.fromCharCode(view.getUint8(4), view.getUint8(5), view.getUint8(6), view.getUint8(7))
    if (size === 1) size = view.getUint32(8) * 2 ** 32 + view.getUint32(12) // 64-bit size
    else if (size === 0) size = blob.size - offset // runs to the end of the file
    if (size < 8) throw new Error(`corrupt MP4 box "${type}" at ${offset}`)
    boxes.push({ type, start: offset, end: Math.min(offset + size, blob.size) })
    offset += size
  }
  return boxes
}

/** Byte ranges to append in order: the header (everything before the first `moof`), then one
 *  range per fragment (a `moof` and whatever follows it until the next one). */
function segmentsOf(boxes: Box[]): Array<[number, number]> {
  const firstMoof = boxes.findIndex((b) => b.type === 'moof')
  if (firstMoof <= 0) throw new Error('not a fragmented MP4 (no moof after the header)')
  const segments: Array<[number, number]> = [[0, boxes[firstMoof].start]]
  let current: [number, number] | null = null
  for (const box of boxes.slice(firstMoof)) {
    if (box.type === 'moof') {
      if (current) segments.push(current)
      current = [box.start, box.end]
    } else if (current) {
      current[1] = box.end
    }
  }
  if (current) segments.push(current)
  return segments
}

export interface StreamFeed {
  /** Stops feeding and lets go of the MediaSource. Safe to call more than once. */
  destroy(): void
}

/**
 * Starts feeding [blobUrl] (an object URL of the stored copy) into [video]. [onError] is called
 * at most once, with a reason, when the browser refuses the file or its codecs — the caller then
 * plays the video from its network address instead.
 */
export function feedStream(
  video: HTMLVideoElement,
  blobUrl: string,
  mime: string,
  onError: (reason: string) => void,
): StreamFeed {
  let stopped = false
  let failed = false
  const fail = (reason: string) => {
    if (stopped || failed) return
    failed = true
    onError(reason)
  }

  const MS = window.MediaSource
  if (!MS || !MS.isTypeSupported(mime)) {
    fail(`this browser can't play ${mime}`)
    return { destroy() {} }
  }

  const mediaSource = new MS()
  const sourceUrl = URL.createObjectURL(mediaSource)
  video.src = sourceUrl

  const waitFor = (target: EventTarget, event: string, ms: number) =>
    new Promise<void>((resolve) => {
      const done = () => {
        clearTimeout(timer)
        target.removeEventListener(event, done)
        resolve()
      }
      const timer = setTimeout(done, ms)
      target.addEventListener(event, done)
    })

  const run = async () => {
    await waitFor(mediaSource, 'sourceopen', 10_000)
    if (stopped) return
    if (mediaSource.readyState !== 'open') throw new Error('MediaSource never opened')

    const blob = await (await fetch(blobUrl)).blob()
    const segments = segmentsOf(await topLevelBoxes(blob))
    const buffer = mediaSource.addSourceBuffer(mime)

    const append = (bytes: ArrayBuffer) =>
      new Promise<void>((resolve, reject) => {
        const onEnd = () => { cleanup(); resolve() }
        const onErr = () => { cleanup(); reject(new Error('the browser rejected a piece of the video')) }
        const cleanup = () => {
          buffer.removeEventListener('updateend', onEnd)
          buffer.removeEventListener('error', onErr)
        }
        buffer.addEventListener('updateend', onEnd)
        buffer.addEventListener('error', onErr)
        buffer.appendBuffer(bytes)
      })

    const bufferedAhead = () => {
      const t = video.currentTime
      for (let i = 0; i < buffer.buffered.length; i++) {
        if (buffer.buffered.start(i) <= t + 0.5 && buffer.buffered.end(i) >= t) return buffer.buffered.end(i) - t
      }
      return 0
    }

    for (const [start, end] of segments) {
      while (!stopped && bufferedAhead() > BUFFER_AHEAD_SECONDS) await waitFor(video, 'timeupdate', 1_000)
      if (stopped) return
      const bytes = await blob.slice(start, end).arrayBuffer()
      if (stopped) return
      try {
        await append(bytes)
      } catch (e) {
        // Buffer full: drop what has already played, then try the same piece again once.
        if ((e as DOMException)?.name !== 'QuotaExceededError' || video.currentTime <= KEEP_BEHIND_SECONDS) throw e
        await new Promise<void>((resolve) => {
          buffer.addEventListener('updateend', () => resolve(), { once: true })
          buffer.remove(0, video.currentTime - KEEP_BEHIND_SECONDS)
        })
        await append(bytes)
      }
    }
    if (!stopped && mediaSource.readyState === 'open') mediaSource.endOfStream()
  }

  run().catch((e) => fail((e as Error)?.message || String(e)))

  return {
    destroy() {
      if (stopped) return
      stopped = true
      URL.revokeObjectURL(sourceUrl)
    },
  }
}
