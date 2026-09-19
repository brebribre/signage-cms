<script setup lang="ts">
import IconCalendar from '~icons/material-symbols/calendar-month-outline'
import IconCloudOff from '~icons/material-symbols/cloud-off-outline'
import IconFactCheck from '~icons/material-symbols/fact-check-outline'
import IconPalette from '~icons/material-symbols/palette-outline'
import IconPower from '~icons/material-symbols/power-settings-new'
import IconUpdate from '~icons/material-symbols/system-update'

const FEATURES = [
  { icon: IconPalette, title: 'Scenes, not slides', text: 'Place pictures, video, live websites and text on one canvas, Canva-style. Crop, layer, rotate, blur the background. It looks the same on the wall as it does on your screen.' },
  { icon: IconCalendar, title: 'Campaigns that know the time', text: 'Loop one playlist all day, or schedule several by day and hour with a date range. Every screen resolves what to show on its own clock, in its own timezone.' },
  { icon: IconFactCheck, title: 'Reviews for teams', text: 'Managers build freely. Anything that would change a screen waits for the owner, with a Before and After preview, an Approve, and a note back if not.' },
  { icon: IconPower, title: 'Remote control', text: 'Power schedules, brightness, volume, rotation and a touch lock, from the screen’s own page — alongside what it is playing, and why, right now.' },
  { icon: IconUpdate, title: 'Updates over the air', text: 'Roll a new player build out to the fleet, or to one screen, with progress and reasons. Screens install it themselves and come back playing.' },
  { icon: IconCloudOff, title: 'Keeps playing offline', text: 'Every file is stored on the screen, downloads resume after a power cut, and a screen that loses the network keeps its loop going regardless.' },
]
</script>

<template>
  <!-- Stripe's two-column section: the heading holds still on the left while the detail scrolls
       past it on the right. On a phone it collapses to one column, heading first. -->
  <section id="product" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="grid gap-10 lg:grid-cols-12 lg:gap-16">
      <div class="lg:col-span-4">
        <div class="lg:sticky lg:top-28">
          <p class="reveal text-[13px] font-medium uppercase tracking-wider text-brand">What you get</p>
          <h2 class="reveal mt-3 text-3xl leading-tight sm:text-4xl">Everything a wall of screens needs, nothing it doesn’t.</h2>
          <p class="reveal mt-4 leading-relaxed text-ink-muted">
            Paskall is built around the question a morning starts with: what is playing, what is waiting,
            what went wrong. Every feature answers one of those.
          </p>
        </div>
      </div>
      <ul class="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:col-span-8">
        <li v-for="f in FEATURES" :key="f.title" class="reveal">
          <span class="inline-flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand">
            <component :is="f.icon" class="size-5" />
          </span>
          <h3 class="mt-4 text-lg">{{ f.title }}</h3>
          <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ f.text }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
