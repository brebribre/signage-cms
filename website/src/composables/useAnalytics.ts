/**
 * Google Analytics 4, behind a cookie notice.
 *
 * Google's Consent Mode starts with every kind of storage denied: until a visitor accepts, GA
 * sets no cookies and sends only anonymous, cookieless pings, which Google uses to estimate the
 * rest. Accepting turns on analytics cookies; ads storage stays off, since the site runs no ads.
 * The choice is kept in this browser, and the notice doesn't ask again.
 *
 * With no measurement id nothing loads at all, which is also how local development runs.
 */
import { ref } from 'vue'

/** The GA4 web stream's measurement id (Admin → Data streams). Public by nature: it is in
 *  every page Google Analytics runs on. */
const GA_ID = 'G-CE9NZMZ0WC'

const STORAGE_KEY = 'marien.consent'
type Choice = 'granted' | 'denied'

declare global {
  interface Window { dataLayer: unknown[]; gtag?: (...args: unknown[]) => void }
}

function readChoice(): Choice | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'granted' || v === 'denied' ? v : null
  } catch {
    return null
  }
}

/** The visitor's answer to the notice; null until they give one. */
export const consent = ref<Choice | null>(readChoice())
export const analyticsOn = !!GA_ID

/** Load GA once, at startup, with consent as the visitor last left it. */
export function initAnalytics() {
  if (!GA_ID) return
  window.dataLayer = window.dataLayer || []
  window.gtag = function () {
    // gtag.js reads the arguments object itself, not an array.
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer.push(arguments)
  }
  window.gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: consent.value === 'granted' ? 'granted' : 'denied',
  })
  window.gtag('js', new Date())
  window.gtag('config', GA_ID)
  const s = document.createElement('script')
  s.async = true
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`
  document.head.appendChild(s)
}

export function setConsent(choice: Choice) {
  consent.value = choice
  try { localStorage.setItem(STORAGE_KEY, choice) } catch { /* asked again next visit */ }
  window.gtag?.('consent', 'update', { analytics_storage: choice })
}

/** One event: what a visitor did (a GA4 event name) and where on the page they did it. */
export function track(event: string, params: Record<string, string> = {}) {
  window.gtag?.('event', event, params)
}
