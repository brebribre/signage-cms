/**
 * Which of the site's pages this is: the home page, /features with every feature on its own card,
 * /software with the CMS and the two players, /android with the Android player's downloads, or /demo with the filmed demo. The server answers every path with the same index.html, so the
 * path is read once here rather than through a router.
 */
export type Page = 'home' | 'features' | 'software' | 'android' | 'demo'

const PATHS: Record<string, Page> = { '/features': 'features', '/software': 'software', '/android': 'android', '/demo': 'demo' }

export const page: Page = PATHS[location.pathname.replace(/\/+$/, '')] ?? 'home'

/** A link to a section of the home page that works from any page. */
export const homeSection = (id: string) => (page === 'home' ? `#${id}` : `/#${id}`)
