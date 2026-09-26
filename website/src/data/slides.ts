/** What the demo screens play, and what the little CMS among them lists. One source, so the
 *  panel and the screens can never disagree about what is on air. Each slide is drawn by
 *  SlideArt in the site's own look; the words come from the current language. */
import { computed } from 'vue'

import { useI18n } from '@/i18n'

/** A slide's look: which of the three backgrounds, and its icon. */
export type SlideTone = 'light' | 'sky' | 'tint'
export type SlideIcon = 'clock' | 'dish' | 'work' | 'wave'

export interface Slide {
  /** What the playlist is called in the CMS panel. */
  name: string
  /** The line the screen shows, and the smaller one under it. */
  title: string
  sub: string
  tone: SlideTone
  icon: SlideIcon
}

const LOOKS: Pick<Slide, 'tone' | 'icon'>[] = [
  { tone: 'light', icon: 'clock' },
  { tone: 'sky', icon: 'dish' },
  { tone: 'tint', icon: 'work' },
  { tone: 'light', icon: 'wave' },
]
export const SLIDE_COUNT = LOOKS.length

export function useSlides() {
  const { m } = useI18n()
  return computed<Slide[]>(() => LOOKS.map((look, i) => ({ ...m.value.slides[i], ...look })))
}
