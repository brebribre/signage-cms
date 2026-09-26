/**
 * Which of the site's pages this is: the home page, /how-it-works with the feature cards, /features with every feature on its own card,
 * /software with the CMS and the two players, /android with the Android player's downloads, or /demo with the filmed demo. The server answers every path with the same index.html, so the
 * path is read once here rather than through a router.
 */
export type Page = 'home' | 'how' | 'features' | 'software' | 'android' | 'demo'

const PATHS: Record<string, Page> = { '/how-it-works': 'how', '/features': 'features', '/software': 'software', '/android': 'android', '/demo': 'demo' }

export const page: Page = PATHS[location.pathname.replace(/\/+$/, '')] ?? 'home'

/** A link to a section of the home page that works from any page. */
export const homeSection = (id: string) => (page === 'home' ? `#${id}` : `/#${id}`)
