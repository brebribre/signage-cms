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
    title: 'Marien. Digital signage that runs itself',
    description: 'Marien puts pictures, videos and live websites on every screen you own: digital signage, smart TVs and Android boxes.',
  },
  lang: { label: 'Language', en: 'English', id: 'Bahasa Indonesia' },
  nav: {
    label: 'Site',
    menu: 'Menu',
    links: { screens: 'Screens', content: 'Content', publish: 'Publish', platforms: 'Platforms', faq: 'FAQ', home: 'Home', features: 'Features', demo: 'Demo' },
    signIn: 'Sign in',
    requestAccess: 'Request access',
  },
  hero: {
    title: 'The smart way to run your screens.',
    subtitle: 'Pictures, videos and websites, on any display.',
    cta: 'Request access',
    demo: 'See demo',
    campaign: 'Store campaign',
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
    label: 'Where Marien runs',
    items: ['Cafés', 'LOBBIES', 'clinics', 'Retail', 'CAMPUSES', 'Restaurants', 'Hotels', 'SHOWROOMS'],
  },
  /** A statement: the lead in ink, the rest in grey at the same size. */
  features: {
    lead: 'Marien is a CMS for Digital Signage.',
    rest: 'Connect a screen, design what it plays, and publish everywhere at once.',
  },
  connect: {
    title: 'Connect your screens',
    body: 'Type the six-letter code from the player, and the screen joins your fleet.',
    statUnder: 'Under',
    statValue: '1 min',
    statCaption: 'To connect a new screen',
    photoAlt: 'The pairing code on a new Marien screen',
  },
  design: {
    tablist: 'The editor',
    inMarien: 'in Marien',
    seeAll: 'See all features',
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
    rest: 'Marien CMS works on your phone, tablet and monitor.',
    monitorAlt: 'The Marien dashboard on a monitor',
  },
  featuresPage: {
    metaTitle: 'Marien. Features',
    lead: 'Everything in Marien.',
    rest: 'From the first design to the team that runs your screens.',
    more: [
      { label: 'Users', title: 'Delegate tasks.', text: 'Give each teammate their own sign-in, limited to the screens you choose.' },
      { label: 'Reviews', title: 'Review before it airs.', text: 'Changes from your team wait for your approval before they reach a screen.' },
    ],
  },
  demo: {
    metaTitle: 'Marien. Demo',
    title: 'Connecting a Screen to Publishing Content',
    videoLabel: 'Demo: the Marien CMS beside a screen that changes as each step is done',
    left: 'Marien CMS',
    right: 'The screen',
  },
  seeDemo: {
    title: 'See the Demo',
    videoLabel: 'Demo: pairing a screen in the Marien CMS and deploying to it, beside the screen itself',
  },
  faq: {
    title: 'Frequently Asked Questions',
    more: 'Something else?',
    write: 'Write to us',
    items: [
      { q: 'What hardware do I need?', a: 'Any Android TV box or tablet, or a smart TV with a browser. Full remote control needs the Android player set up as Device Owner, which we can do for you.' },
      { q: 'What happens when the wifi drops?', a: 'The screen keeps playing. Its pictures and videos are saved on the screen itself, so what is on air carries on without the internet. Changes you publish in the meantime wait, and the screen picks up the latest version shortly after the wifi comes back.' },
      { q: 'Can staff change content safely?', a: 'Yes. They get the screens you grant, and anything that would change a screen waits for your approval.' },
      { q: 'How big can a video be?', a: 'Upload the original. Marien makes a copy every screen can play, 4K for Android boxes and 1080p for TV browsers.' },
    ],
  },
  footer: {
    title: 'Put your first screen on Marien',
    body: 'Leave your details and we’ll get in touch to set up your account.',
    cta: 'Request access',
    signIn: 'Sign in',
    form: {
      name: 'Name',
      company: 'Company',
      optional: '(optional)',
      email: 'Email',
      phone: 'Phone number',
      eitherHint: 'An email or a phone number, whichever you prefer. At least one.',
      sending: 'Sending…',
      sentTitle: 'Thank you!',
      sentBody: 'We’ve got your request and will be in touch soon.',
      errors: {
        name: 'Please enter your name.',
        contact: 'Please leave an email or a phone number so we can reach you.',
        email: 'That email doesn’t look right.',
        phone: 'That phone number doesn’t look right.',
        send: 'That didn’t go through. Check your connection and try again.',
      },
    },
  },
}

export type Messages = typeof en
export default en
