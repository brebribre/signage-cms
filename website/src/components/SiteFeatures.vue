<script setup lang="ts">
import IconCalendar from '~icons/material-symbols/calendar-month-outline'
import IconCloudOff from '~icons/material-symbols/cloud-off-outline'
import IconFactCheck from '~icons/material-symbols/fact-check-outline'
import IconPalette from '~icons/material-symbols/palette-outline'
import IconPower from '~icons/material-symbols/power-settings-new'
import IconUpdate from '~icons/material-symbols/system-update'

const FEATURES = [
  { icon: IconPalette, title: 'Scenes, not slides', text: 'Photos, video, live websites and text on one canvas. Crop, layer, blur.' },
  { icon: IconCalendar, title: 'Schedules', text: 'One loop all day, or rules by hour and weekday. Each screen keeps its own clock.' },
  { icon: IconFactCheck, title: 'Approvals', text: 'Staff changes wait for your yes, with a before and after preview.' },
  { icon: IconPower, title: 'Remote control', text: 'Power, brightness, volume and rotation, from the screen’s page.' },
  { icon: IconUpdate, title: 'Updates over the air', text: 'Push a new player build to the fleet. Screens install it and come back playing.' },
  { icon: IconCloudOff, title: 'Works offline', text: 'Files live on the screen. Lose the network and the loop keeps running.' },
]
</script>

<template>
  <section id="product" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="grid gap-10 lg:grid-cols-12 lg:gap-16">
      <div class="lg:col-span-4">
        <div class="lg:sticky lg:top-28">
          <p class="reveal text-[13px] font-medium uppercase tracking-wider text-brand">What you get</p>
          <h2 class="reveal mt-3 text-3xl leading-tight sm:text-4xl">Built for walls that have to be right.</h2>
        </div>
      </div>
      <ul class="grid gap-x-10 gap-y-9 sm:grid-cols-2 lg:col-span-8">
        <li v-for="f in FEATURES" :key="f.title" class="reveal">
          <span class="inline-flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand">
            <component :is="f.icon" class="size-5" />
          </span>
          <h3 class="mt-4 text-lg">{{ f.title }}</h3>
          <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ f.text }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
