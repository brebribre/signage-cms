<script setup lang="ts">
/**
 * The CMS's overview at phone or tablet size, drawn in markup so it stays sharp at any width.
 * Every length is in container units (cqw), so the whole screen scales with the device frame
 * it sits in, the way a real screenshot would, without a screenshot to keep up to date.
 *
 * Its labels are the CMS's own and stay in English, as the CMS is; the playlist names are the
 * customer's and follow the page's language.
 */
import IconMenu from '~icons/material-symbols/menu'

import mark from '@/assets/paskall-mark.png'
import SlideArt from './SlideArt.vue'
import { useSlides } from '@/data/slides'

defineProps<{ size: 'phone' | 'tablet' }>()

const slides = useSlides()
</script>

<template>
  <div class="@container size-full overflow-hidden bg-page text-left">
    <!-- Phone: one column, the stats stacked. -->
    <div v-if="size === 'phone'" class="p-[6cqw] pt-[5cqw]">
      <div class="flex items-center justify-between text-[5cqw] font-semibold text-ink">
        <span>9:41</span><span class="h-[4cqw] w-[9cqw] rounded-[1.5cqw] border-[0.6cqw] border-ink/70" />
      </div>
      <div class="mt-[6cqw] flex items-center justify-between">
        <img :src="mark" alt="" class="h-[8cqw] w-auto" />
        <IconMenu class="size-[8cqw] text-ink" aria-hidden="true" />
      </div>
      <p class="display mt-[7cqw] text-[11cqw] leading-none text-ink">Overview</p>
      <p class="mt-[2cqw] text-[4.5cqw] text-ink-muted">What every screen is playing</p>
      <div class="mt-[6cqw] rounded-[5cqw] bg-gradient-to-br from-brand to-brand-bright p-[5cqw] text-white">
        <p class="text-[4.5cqw] opacity-80">Screens</p>
        <p class="display text-[12cqw] leading-tight">6</p>
        <p class="text-[4.5cqw] opacity-80">2 online now</p>
      </div>
      <div class="mt-[3cqw] grid grid-cols-2 gap-[3cqw]">
        <div class="rounded-[5cqw] bg-white p-[4cqw]">
          <p class="text-[4cqw] text-ink-muted">Campaigns</p>
          <p class="display text-[9cqw] text-ink">1</p>
        </div>
        <div class="rounded-[5cqw] bg-white p-[4cqw]">
          <p class="text-[4cqw] text-ink-muted">Errors</p>
          <p class="display text-[9cqw] text-ink">0</p>
        </div>
      </div>
      <p class="mt-[6cqw] text-[5cqw] font-medium text-ink">Now playing</p>
      <ul class="mt-[3cqw] flex flex-col gap-[2.5cqw]">
        <li v-for="i in [0, 1, 3]" :key="i" class="flex items-center gap-[3cqw] rounded-[4cqw] bg-white p-[2.5cqw]">
          <span class="h-[10cqw] w-[15cqw] shrink-0 overflow-hidden rounded-[2.5cqw]"><SlideArt :slide="slides[i]" thumb /></span>
          <span class="min-w-0 flex-1 truncate text-[4.5cqw] text-ink">{{ slides[i].name }}</span>
          <span class="size-[2.5cqw] rounded-full bg-emerald-500" />
        </li>
      </ul>
    </div>

    <!-- Tablet: the stats in a grid of four, the list under them. -->
    <div v-else class="p-[5cqw]">
      <div class="flex items-center justify-between">
        <img :src="mark" alt="" class="h-[5cqw] w-auto" />
        <IconMenu class="size-[5cqw] text-ink" aria-hidden="true" />
      </div>
      <p class="display mt-[5cqw] text-[7cqw] leading-none text-ink">Overview</p>
      <p class="mt-[1.5cqw] text-[3cqw] text-ink-muted">What every screen is playing, right now, and why.</p>
      <div class="mt-[4cqw] grid grid-cols-2 gap-[2.5cqw]">
        <div class="rounded-[3cqw] bg-gradient-to-br from-brand to-brand-bright p-[3.5cqw] text-white">
          <p class="text-[2.8cqw] opacity-80">Screens</p>
          <p class="display text-[7cqw] leading-tight">6</p>
          <p class="text-[2.6cqw] opacity-80">2 online now</p>
        </div>
        <div v-for="c in [['Campaigns', '1', 'Across 3 screens'], ['Reporting errors', '0', 'In the last 24 hours'], ['Storage', '14 MB', 'No quota set']]" :key="c[0]" class="rounded-[3cqw] bg-white p-[3.5cqw]">
          <p class="text-[2.8cqw] text-ink-muted">{{ c[0] }}</p>
          <p class="display text-[7cqw] leading-tight text-ink">{{ c[1] }}</p>
          <p class="text-[2.6cqw] text-ink-subtle">{{ c[2] }}</p>
        </div>
      </div>
      <div class="mt-[5cqw] flex gap-[4cqw] border-b border-line text-[3cqw]">
        <span class="border-b-[0.5cqw] border-ink pb-[1.5cqw] text-ink">Now playing</span>
        <span class="text-ink-subtle">Pending review</span>
        <span class="text-ink-subtle">Errors</span>
      </div>
      <ul class="mt-[3cqw] flex flex-col gap-[2cqw]">
        <li v-for="(s, i) in slides" :key="i" class="flex items-center gap-[3cqw] rounded-[2.5cqw] bg-white p-[2cqw]">
          <span class="h-[7cqw] w-[11cqw] shrink-0 overflow-hidden rounded-[1.5cqw]"><SlideArt :slide="s" thumb /></span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[3cqw] text-ink">{{ s.name }}</span>
            <span class="block truncate text-[2.4cqw] text-ink-subtle">{{ s.title }}</span>
          </span>
          <span class="rounded-full bg-emerald-50 px-[2cqw] py-[0.8cqw] text-[2.4cqw] text-emerald-700">Playing</span>
        </li>
      </ul>
    </div>
  </div>
</template>
