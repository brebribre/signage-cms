/** What the hero's screens can play, and what the little CMS among them lists. One source, so the
 *  panel and the screen can never disagree about what is on air. The pictures are fixed; the
 *  words come from the current language. */
import { computed } from 'vue'

import { useI18n } from '@/i18n'

export interface Slide {
  /** What the playlist is called in the CMS panel. */
  name: string
  /** The line the screen shows. */
  title: string
  sub: string
  /** A photo behind the words, or a gradient when there is none. */
  src?: string
  from?: string
  to?: string
}

const LOOKS: Pick<Slide, 'src' | 'from' | 'to'>[] = [
  { from: '#002f96', to: '#0076dd' },
  { src: '/shots/screen-totem.webp' },
  { from: '#00184d', to: '#1f55c4' },
  { src: '/shots/screen-lobby.webp' },
]
export const SLIDE_COUNT = LOOKS.length

export function useSlides() {
  const { m } = useI18n()
  return computed<Slide[]>(() => LOOKS.map((look, i) => ({ ...m.value.slides[i], ...look })))
}
