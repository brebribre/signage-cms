/**
 * Which of the site's two pages this is: the home page, or /demo with the filmed demo. The
 * server answers every path with the same index.html, so the path is read once here rather than
 * through a router.
 */
export const isDemoPage = location.pathname.replace(/\/+$/, '') === '/demo'

/** A link to a section of the home page that works from either page. */
export const homeSection = (id: string) => (isDemoPage ? `/#${id}` : `#${id}`)
