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
    links: { screens: 'Screens', content: 'Content', publish: 'Publish', platforms: 'Platforms', home: 'Home', features: 'Features', demo: 'Demo' },
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
    lead: 'Marien is a Content Management System for Digital Signage.',
    rest: 'Connect a screen, design what it plays, and publish everywhere at once.',
  },
  /** What people run Marien for, each shown on a real-looking screen. */
  uses: {
    items: [
      { title: 'Advertising', alt: 'A Marien signage totem in a busy mall, playing a café promotion' },
      { title: 'Information Sharing', alt: 'A Marien screen above a crowded station hall, showing the next departures' },
      { title: 'Interactive Media', alt: 'A shopper tapping a mall directory website on a Marien touch screen' },
    ],
  },
  /** The statement over the feature cards: the lead in ink, the rest in the brand gradient. */
  how: {
    lead: 'Set up your device',
    rest: 'and display your first content in less than 5 minutes.',
  },
  /** The first of the feature cards: the two things to set up before anything else. */
  start: {
    title: 'Set up your device',
    body: 'Two things, and your screen is ready to go.',
    player: {
      title: 'Put Marien Player on the screen',
      text: 'On an Android TV box, install the app. On a smart TV, open the web player in its browser.',
      android: 'Download for Android',
      web: 'Open the web player',
    },
    cms: {
      title: 'Open Marien CMS',
      text: 'Sign in from your phone, tablet or laptop, and connect the screen with its code.',
      open: 'Open Marien CMS',
    },
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
  footer: {
    /** Followed by the Marien wordmark, which stands in for the name. */
    title: 'Put your first screen on',
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
