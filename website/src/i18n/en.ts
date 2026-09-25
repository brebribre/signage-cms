/**
 * Every word the site says, in English. The Indonesian file mirrors this shape exactly (its
 * type is this object's), so a missing or misspelt key is a build error rather than a blank.
 *
 * Words that are the CMS's own interface (its sidebar, "On air", the overview's labels) are not
 * here: the CMS is in English, so the pictures of it stay in English in both languages. What a
 * customer would type into it (campaign and playlist names, what a slide says) is here, because
 * a customer in Jakarta would type it in Indonesian.
 */
const en = {
  meta: {
    title: 'Paskall. Digital signage that runs itself',
    description: 'Paskall puts pictures, videos and live websites on every screen you own: digital signage, smart TVs and Android boxes.',
  },
  lang: { label: 'Language', en: 'English', id: 'Bahasa Indonesia' },
  nav: {
    label: 'Site',
    menu: 'Menu',
    links: { screens: 'Screens', content: 'Content', publish: 'Publish', platforms: 'Platforms', faq: 'FAQ' },
    signIn: 'Sign in',
    requestAccess: 'Request access',
  },
  hero: {
    title: 'The smart way to run your screens.',
    subtitle: 'Pictures, videos and websites, on any display.',
    cta: 'Request access',
    screens: [
      { name: 'Lobby TV', kind: 'Android box' },
      { name: 'Entrance totem', kind: 'Smart TV' },
      { name: 'Reception', kind: 'Android box' },
      { name: 'Cafe screen', kind: 'Browser' },
    ],
    campaign: 'Store campaign',
    hint: 'Pick a playlist. Every screen changes.',
    picker: 'What the screens play',
    /** The cards floating round the CMS on a wide page. */
    press: { value: '1 press', label: 'To update every screen' },
    any: { value: 'Any screen', label: 'Android, smart TVs and browsers' },
    pair: 'Pair a screen with a six-letter code',
  },
  /** What the demo screens play, and what the demo CMS calls each playlist. */
  slides: [
    { name: 'Opening hours', title: 'Open until 9pm', sub: 'Kitchen closes at 8:30' },
    { name: 'Lunch menu', title: 'Today’s special', sub: 'Ask at the counter' },
    { name: 'Recruiting', title: 'Now hiring', sub: 'Scan at reception' },
    { name: 'Welcome', title: 'Welcome', sub: 'Wifi: guest' },
  ],
  online: 'Online',
  venues: {
    label: 'Where Paskall runs',
    items: ['Cafés', 'LOBBIES', 'clinics', 'Retail', 'CAMPUSES', 'Restaurants', 'Hotels', 'SHOWROOMS'],
  },
  /** A statement: the lead in ink, the rest in grey at the same size. */
  features: {
    lead: 'Paskall is a CMS for Digital Signage.',
    rest: 'Connect a screen, design what it plays, and publish everywhere at once.',
  },
  connect: {
    title: 'Connect your screens',
    body: 'Type the six-letter code from the player, and the screen joins your fleet.',
    statUnder: 'Under',
    statValue: '1 min',
    statCaption: 'To connect a new screen',
    live: 'Live',
    photoAlt: 'A cafe screen run by Paskall',
    screens: [
      { name: 'Lobby TV', kind: 'Android box' },
      { name: 'Entrance totem', kind: 'Smart TV' },
      { name: 'Cafe screen', kind: 'Browser' },
    ],
  },
  design: {
    tablist: 'The editor',
    inPaskall: 'in Paskall',
    tabs: [
      { label: 'Design', title: 'Design your content.', text: 'Photos, video, websites and text, at the screen’s real shape.' },
      { label: 'Playlist', title: 'Play them in order.', text: 'Set the order, and how long each one plays.' },
      { label: 'Schedule', title: 'Say where and when.', text: 'Pick the screens and the hours, by time and weekday.' },
    ],
  },
  publish: {
    title: 'Publish them effortlessly',
    body: 'Changes are published in seconds.',
    ready: 'Ready to publish',
    sending: 'Sending to screens',
    live: 'Live on every screen',
    button: 'Publish',
    publishing: 'Publishing',
    published: 'Published',
    screens: [
      { name: 'Lobby TV', kind: 'Android box' },
      { name: 'Entrance', kind: 'Smart TV' },
      { name: 'Cafe', kind: 'Browser' },
    ],
  },
  platforms: {
    lead: 'Designed for versatility.',
    rest: 'One player, on whatever screen you already have.',
    items: [
      { name: 'Android', text: 'Install our .apk on Android TV boxes and devices.' },
      { name: 'Smart TV browser', text: 'Utilizes the smart TV’s browser and requires no installation.' },
      { name: 'Browser', text: 'Any device that runs a browser.' },
    ],
  },
  responsive: {
    lead: 'Observe from anywhere.',
    rest: 'Paskall CMS works on your phone, tablet and monitor.',
    monitorAlt: 'The Paskall dashboard on a monitor',
  },
  faq: {
    title: 'Frequently Asked Questions',
    more: 'Something else?',
    write: 'Write to us',
    items: [
      { q: 'What hardware do I need?', a: 'Any Android TV box or tablet, or a smart TV with a browser. Full remote control needs the Android player set up as Device Owner, which we can do for you.' },
      { q: 'What happens when the internet drops?', a: 'Nothing visible. Files live on the screen, so the loop keeps playing and catches up when the network returns.' },
      { q: 'Can staff change content safely?', a: 'Yes. They get the screens you grant, and anything that would change a screen waits for your approval.' },
      { q: 'How big can a video be?', a: 'Upload the original. Paskall makes a copy every screen can play, 4K for Android boxes and 1080p for TV browsers.' },
    ],
  },
  footer: {
    title: 'Put your first screen on Paskall',
    body: 'Tell us how many screens. We’ll set up the account.',
    cta: 'Request access',
    signIn: 'Sign in',
    mailSubject: 'Paskall access',
  },
}

export type Messages = typeof en
export default en
