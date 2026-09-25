/** What the hero's screens can play, and what the little CMS among them lists. One source, so the
 *  panel and the screen can never disagree about what is on air. */
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

export const SLIDES: Slide[] = [
  { name: 'Opening hours', title: 'Open until 9pm', sub: 'Kitchen closes at 8:30', from: '#002f96', to: '#0076dd' },
  { name: 'Lunch menu', title: 'Today’s special', sub: 'Ask at the counter', src: '/shots/screen-totem.webp' },
  { name: 'Recruiting', title: 'Now hiring', sub: 'Scan at reception', from: '#00184d', to: '#1f55c4' },
  { name: 'Welcome', title: 'Welcome', sub: 'Wifi: guest', src: '/shots/screen-lobby.webp' },
]
