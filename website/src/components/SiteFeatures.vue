<script setup lang="ts">
import IconCalendar from '~icons/material-symbols/calendar-month-outline'
import IconCloudOff from '~icons/material-symbols/cloud-off-outline'
import IconFactCheck from '~icons/material-symbols/fact-check-outline'
import IconPalette from '~icons/material-symbols/palette-outline'
import IconPower from '~icons/material-symbols/power-settings-new'
import IconUpdate from '~icons/material-symbols/system-update'

const FEATURES = [
  { icon: IconPalette, title: 'Scenes, not slides', text: 'Place pictures, video, live websites and text on one canvas, Canva-style. Crop, layer, rotate, blur the background. It looks the same on the wall as on your screen.' },
  { icon: IconCalendar, title: 'Campaigns that know the time', text: 'Loop one playlist all day, or schedule several by day and hour with a date range. Every screen resolves what to show on its own clock.' },
  { icon: IconFactCheck, title: 'Reviews for teams', text: 'Managers build freely. Anything that would change a screen waits for the owner, with a Before and After preview, an Approve, and a note back.' },
  { icon: IconPower, title: 'Remote control', text: 'Power schedules, brightness, volume, rotation and a touch lock, from the screen’s page. See what it is playing and why, right now.' },
  { icon: IconUpdate, title: 'Updates over the air', text: 'Roll a new player build out to the fleet, or one screen, with progress and reasons. Screens install it themselves and come back playing.' },
  { icon: IconCloudOff, title: 'Keeps playing offline', text: 'Every file is stored on the screen, downloads resume after a power cut, and a screen that loses the network keeps its loop going.' },
]
</script>

<template>
  <section id="product" class="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="reveal max-w-2xl">
      <p class="text-[13px] uppercase tracking-wider text-brand">What you get</p>
      <h2 class="mt-3 text-3xl sm:text-4xl">Everything a wall of screens needs, nothing it doesn’t.</h2>
      <p class="mt-4 text-ink-muted">
        Paskall was built around one question a morning starts with: what is playing, what is waiting, what went wrong. Every feature answers one of those.
      </p>
    </div>
    <ul class="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <li v-for="f in FEATURES" :key="f.title" class="reveal group rounded-2xl border border-line bg-canvas p-6 transition-colors hover:border-brand/40">
        <span class="inline-flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand transition-colors group-hover:bg-brand group-hover:text-ink-inverse">
          <component :is="f.icon" class="size-5" />
        </span>
        <h3 class="mt-4 text-lg">{{ f.title }}</h3>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ f.text }}</p>
      </li>
    </ul>
  </section>
</template>
