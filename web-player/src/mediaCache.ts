/**
 * Files kept in the browser, keyed by **checksum** — the Android player's `data/MediaCache.kt`,
 * on the Cache Storage API.
 *
 * Checksum, not URL, for the same reason as there: the manifest's presigned URLs are re-issued on
 * every fetch, so keying on the URL would re-download the whole playlist several times a day.
 *
 * Playback reads a cached file through an object URL made from its stored blob. Those are kept
 * for as long as the file stays in the manifest, so a slot coming round again reuses the same
 * URL rather than minting (and leaking) a new one each loop.
 */

export interface MediaStore {
  /** False when this browser cannot store files at all — see [CacheStorageMedia.available]. */
  readonly available: boolean
  isCached(checksum: string, bytes: number): Promise<boolean>
  download(checksum: string, url: string, bytes: number): Promise<void>
  /** A URL playback can use for a cached file. Callers check [isCached] first. */
  objectUrl(checksum: string): Promise<string>
  evictExcept(keep: Iterable<string>): Promise<void>
  cachedBytes(): Promise<number>
}

const CACHE_NAME = 'fortu-media-v1'
const BYTES_HEADER = 'x-fortu-bytes'

const keyFor = (checksum: string) => `/__media/${encodeURIComponent(checksum)}`

export class CacheStorageMedia implements MediaStore {
  private urls = new Map<string, string>()

  /** Cache Storage only exists in a secure context (HTTPS, or localhost). A screen opened over
   *  plain HTTP still plays — every file streams from its URL instead — it just cannot survive
   *  losing the network. */
  readonly available = typeof caches !== 'undefined'

  private open() {
    return caches.open(CACHE_NAME)
  }

  async isCached(checksum: string, bytes: number): Promise<boolean> {
    if (!this.available) return false
    const res = await (await this.open()).match(keyFor(checksum))
    // Size as well as existence, like MediaCache.kt: a partial write must never pass for a file.
    // A size of 0 means "not known in advance" (a video thumbnail): stored at all is enough.
    return !!res && (bytes === 0 || Number(res.headers.get(BYTES_HEADER)) === bytes)
  }

  async download(checksum: string, url: string, bytes: number): Promise<void> {
    if (!this.available) throw new Error('this browser cannot store files (not a secure context)')
    let res: Response
    try {
      res = await fetch(url, { mode: 'cors', cache: 'no-store' })
    } catch {
      // A browser reports a CORS refusal and a dead network identically, on purpose. With the
      // manifest having just arrived, the network is usually fine — so name the likelier cause.
      throw new Error("couldn't fetch the file — is this player's address in the R2 bucket's CORS policy?")
    }
    if (!res.ok) throw new Error(`download failed: HTTP ${res.status}`)
    const blob = await res.blob()
    // Read fully before it is stored, so an interrupted transfer can never be mistaken for a
    // complete one — the counterpart of MediaCache.kt's `.part` file and rename.
    if (bytes !== 0 && blob.size !== bytes) throw new Error(`download incomplete: ${blob.size} of ${bytes} bytes`)
    await (await this.open()).put(
      keyFor(checksum),
      new Response(blob, {
        headers: { 'Content-Type': blob.type || 'application/octet-stream', [BYTES_HEADER]: String(blob.size) },
      }),
    )
  }

  async objectUrl(checksum: string): Promise<string> {
    const existing = this.urls.get(checksum)
    if (existing) return existing
    const res = await (await this.open()).match(keyFor(checksum))
    if (!res) throw new Error(`not cached: ${checksum}`)
    const url = URL.createObjectURL(await res.blob())
    this.urls.set(checksum, url)
    return url
  }

  /** Delete anything not in the current manifest — called only after the new set is stored. */
  async evictExcept(keep: Iterable<string>): Promise<void> {
    if (!this.available) return
    const keepKeys = new Set(Array.from(keep, keyFor))
    const cache = await this.open()
    for (const req of await cache.keys()) {
      const path = new URL(req.url).pathname
      if (!keepKeys.has(path)) await cache.delete(req)
    }
    for (const [checksum, url] of this.urls) {
      if (!keepKeys.has(keyFor(checksum))) {
        URL.revokeObjectURL(url)
        this.urls.delete(checksum)
      }
    }
  }

  async cachedBytes(): Promise<number> {
    if (!this.available) return 0
    let total = 0
    const cache = await this.open()
    for (const req of await cache.keys()) {
      const res = await cache.match(req)
      total += Number(res?.headers.get(BYTES_HEADER) ?? 0)
    }
    return total
  }
}
