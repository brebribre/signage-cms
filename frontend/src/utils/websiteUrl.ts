/** Websites on a playlist: what counts as a usable address, and what to call one. */

/** A typed address as a full https:// URL, or null if it isn't one. A missing scheme gets
 *  https:// — people type "example.com". Plain http is refused: screens block it, so it would
 *  save fine and then stay blank. */
export function normalizeWebsiteUrl(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
  try {
    const url = new URL(withScheme)
    if (url.protocol !== 'https:' || !url.hostname.includes('.')) return null
    return url.href
  } catch {
    return null
  }
}

/** A readable name for a website — its host, without "www.". */
export function websiteLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
