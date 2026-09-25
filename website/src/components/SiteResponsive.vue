<script setup lang="ts">
/**
 * The CMS on every size of screen a person might run it from: a monitor with the real
 * dashboard, and a tablet and a phone with the same overview laid out for them. The one dark
 * card on the page, so it lands as a change of pace.
 */
import IconMonitor from '~icons/material-symbols/desktop-windows-outline'
import IconPhone from '~icons/material-symbols/smartphone-outline'
import IconTablet from '~icons/material-symbols/tablet-outline'

import MiniCms from './MiniCms.vue'

const DEVICES = [
  { icon: IconPhone, label: 'Phones' },
  { icon: IconTablet, label: 'Tablets' },
  { icon: IconMonitor, label: 'Monitors' },
]
</script>

<template>
  <section id="responsive" class="mx-auto max-w-7xl px-5 pt-16 sm:px-8 sm:pt-20">
    <div
      class="navy-glow reveal relative overflow-hidden rounded-[2rem] px-5 pt-12 text-white sm:rounded-[2.5rem] sm:px-10 sm:pt-14"
    >
      <!-- Faint rings behind the devices, echoing the hero's dome. -->
      <div class="pointer-events-none absolute -bottom-[30rem] hidden sm:block left-1/2 size-[60rem] -translate-x-1/2 rounded-full border border-white/10" aria-hidden="true" />
      <div class="pointer-events-none absolute -bottom-[22rem] hidden sm:block left-1/2 size-[44rem] -translate-x-1/2 rounded-full border border-white/10" aria-hidden="true" />

      <div class="relative mx-auto max-w-2xl text-center">
        <span class="tag text-accent">Responsive</span>
        <h2 class="mt-4 text-4xl leading-[1.1] sm:text-5xl">Observe from <span class="bg-gradient-to-r from-accent to-[#7fb6ff] bg-clip-text text-transparent">anywhere</span></h2>
        <p class="mt-4 text-lg text-white/75">
          Paskall CMS is designed to be accessible from your phone, tablet and monitor.
        </p>
        <ul class="mt-6 flex flex-wrap justify-center gap-2.5">
          <li v-for="d in DEVICES" :key="d.label" class="flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm ring-1 ring-white/15 backdrop-blur">
            <component :is="d.icon" class="size-4 text-accent" aria-hidden="true" /> {{ d.label }}
          </li>
        </ul>
      </div>

      <!-- The devices. Positions are percentages of the stage, so the group keeps its shape at
           every width, and the window over it shows only their top halves, running off the
           card's foot, so the card stays short. -->
      <div class="relative mx-auto mt-10 aspect-[16/4.2] max-w-5xl overflow-hidden sm:mt-12">
        <div class="absolute inset-x-0 top-0 aspect-[16/9.4]">
          <!-- Monitor. -->
          <div class="absolute left-[15%] top-0 w-[70%]">
            <div class="rounded-[1.4%/2.2%] bg-[#0b0e14] p-[1.1%] shadow-[0_40px_100px_-30px_rgba(0,0,0,0.7)] ring-1 ring-white/15">
              <img src="/shots/overview.webp" alt="The Paskall dashboard on a monitor" class="block aspect-[16/10] w-full rounded-[0.6%/1%] object-cover object-left-top" loading="lazy" decoding="async" />
            </div>
            <div class="mx-auto h-[1.8vw] max-h-6 w-[14%] bg-gradient-to-b from-[#2a2f3a] to-[#171b23]" aria-hidden="true" />
            <div class="mx-auto h-[0.7vw] max-h-2.5 w-[34%] rounded-t-md bg-[#2a2f3a]" aria-hidden="true" />
          </div>

          <!-- Tablet. -->
          <div class="float absolute left-0 top-[20%] w-[27%]" style="--float-delay: -2s">
            <div class="rounded-[9%/7%] bg-[#0b0e14] p-[3.5%] shadow-[0_30px_80px_-24px_rgba(0,0,0,0.75)] ring-1 ring-white/20">
              <div class="aspect-[3/4] overflow-hidden rounded-[5%/4%]">
                <MiniCms size="tablet" />
              </div>
            </div>
          </div>

          <!-- Phone. -->
          <div class="float absolute right-[5%] top-[26%] w-[15%]" style="--float-delay: -4s">
            <div class="rounded-[18%/8.5%] bg-[#0b0e14] p-[5%] shadow-[0_30px_80px_-24px_rgba(0,0,0,0.75)] ring-1 ring-white/20">
              <div class="aspect-[9/19.5] overflow-hidden rounded-[13%/6%]">
                <MiniCms size="phone" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
