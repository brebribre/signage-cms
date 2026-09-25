/**
 * The site's two languages, and how it picks one.
 *
 * Indonesian when the visitor is in Indonesia or reads Indonesian; English otherwise. A browser
 * does not say what country it is in, but it does say its time zone, and Indonesia's four
 * (WIB, WITA, WIT, and Pontianak's) are Indonesia's alone, so the time zone stands in for the
 * country without a geolocation service or a permission prompt. A visitor in Jakarta on an
 * English browser gets Indonesian, and an Indonesian browser abroad does too.
 *
 * A choice made with the switcher wins over all of that and is remembered, and ?lang=en or
 * ?lang=id in the address wins over the remembered choice, so a link can open in either.
 */
import { computed, ref, watchEffect } from 'vue'

import en from './en'
import id from './id'

export type Locale = 'en' | 'id'
export const LOCALES: Locale[] = ['en', 'id']

const MESSAGES = { en, id }
const STORAGE_KEY = 'paskall.locale'
const INDONESIAN_TIME_ZONES = ['Asia/Jakarta', 'Asia/Pontianak', 'Asia/Makassar', 'Asia/Jayapura']

const isLocale = (v: unknown): v is Locale => v === 'en' || v === 'id'

function saved(): Locale | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return isLocale(v) ? v : null
  } catch { return null }
}

/** In Indonesia, by its time zone. */
function inIndonesia(): boolean {
  try {
    return INDONESIAN_TIME_ZONES.includes(Intl.DateTimeFormat().resolvedOptions().timeZone)
  } catch { return false }
}

/** Reads Indonesian: any of the browser's languages is Indonesian ("in" is its old code). */
function readsIndonesian(): boolean {
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language]
  return langs.some((l) => /^(id|in)(-|$)/i.test(l ?? ''))
}

export function detectLocale(): Locale {
  const fromUrl = new URLSearchParams(location.search).get('lang')
  if (isLocale(fromUrl)) return fromUrl
  return saved() ?? (inIndonesia() || readsIndonesian() ? 'id' : 'en')
}

const locale = ref<Locale>(detectLocale())
const m = computed(() => MESSAGES[locale.value])

function setLocale(next: Locale) {
  locale.value = next
  try { localStorage.setItem(STORAGE_KEY, next) } catch { /* private mode: it just isn't remembered */ }
  // Drop a ?lang= that would otherwise overrule this choice on the next visit to the same link.
  const url = new URL(location.href)
  if (url.searchParams.has('lang')) { url.searchParams.delete('lang'); history.replaceState(null, '', url) }
}

// The page's own language, title and description follow the choice.
watchEffect(() => {
  document.documentElement.lang = locale.value
  document.title = m.value.meta.title
  document.querySelector('meta[name="description"]')?.setAttribute('content', m.value.meta.description)
})

export function useI18n() {
  return { locale, m, setLocale }
}
