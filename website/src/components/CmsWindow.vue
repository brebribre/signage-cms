<script setup lang="ts">
/**
 * The CMS, drawn as a small working window rather than a screenshot: the sidebar the real
 * dashboard has, and a campaign's playlists. Pick one and every screen round it changes, which
 * is the product's whole loop in one gesture.
 */
import IconCampaign from '~icons/material-symbols/campaign-outline'
import IconCheck from '~icons/material-symbols/check-circle'
import IconMedia from '~icons/material-symbols/photo-library-outline'
import IconOverview from '~icons/material-symbols/monitoring'
import IconPlaylist from '~icons/material-symbols/playlist-play'
import IconSettings from '~icons/material-symbols/settings-outline'
import IconTv from '~icons/material-symbols/tv-outline'

import mark from '@/assets/paskall-mark.png'
import { useSlides } from '@/data/slides'
import { useI18n } from '@/i18n'

defineProps<{ active: number; screens: number }>()
const emit = defineEmits<{ select: [index: number] }>()

const NAV = [
  { icon: IconOverview, label: 'Overview' },
  { icon: IconMedia, label: 'Media' },
  { icon: IconTv, label: 'Screens' },
  { icon: IconPlaylist, label: 'Playlists' },
  { icon: IconCampaign, label: 'Campaigns', current: true },
  { icon: IconSettings, label: 'Settings' },
]
const { m } = useI18n()
const slides = useSlides()
const thumb = (i: number) => {
  const s = slides.value[i]
  return s.src ? { backgroundImage: `url(${s.src})` } : { background: `linear-gradient(135deg, ${s.from}, ${s.to})` }
}
</script>

<template>
  <figure class="overflow-hidden rounded-t-3xl border border-b-0 border-line bg-canvas shadow-[0_40px_90px_-40px_rgba(0,24,77,0.55)]">
    <!-- The browser chrome. -->
    <div class="flex items-center gap-1.5 border-b border-line bg-surface px-4 py-3">
      <span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" />
      <span class="ml-3 rounded-md bg-canvas px-2.5 py-0.5 text-[11px] text-ink-subtle">app.paskall.co.id</span>
    </div>

    <div class="flex text-left">
      <!-- The sidebar, as the dashboard has it. -->
      <aside class="hidden w-44 shrink-0 border-r border-line p-3 sm:block">
        <img :src="mark" alt="" class="mb-4 ml-1.5 h-6 w-auto" />
        <ul class="flex flex-col gap-0.5">
          <li
            v-for="n in NAV" :key="n.label"
            class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px]"
            :class="n.current ? 'bg-brand-soft text-brand' : 'text-ink-muted'"
          >
            <component :is="n.icon" class="size-4" aria-hidden="true" /> {{ n.label }}
          </li>
        </ul>
      </aside>

      <div class="min-w-0 flex-1 bg-page/60 p-4 sm:p-6">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="display text-xl text-ink sm:text-2xl">{{ m.hero.campaign }}</p>
            <p class="mt-0.5 text-xs text-ink-muted">{{ m.hero.hint }}</p>
          </div>
          <span class="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] text-emerald-700">
            Playing on {{ screens }} of {{ screens }}
          </span>
        </div>

        <ul class="mt-4 flex flex-col gap-2" role="radiogroup" :aria-label="m.hero.picker">
          <li v-for="(s, i) in slides" :key="i">
            <button
              type="button" role="radio" :aria-checked="active === i"
              class="flex w-full items-center gap-3 rounded-2xl bg-canvas p-2 pr-3 text-left ring-1 transition-all duration-200"
              :class="active === i ? 'ring-2 ring-brand' : 'ring-line hover:ring-line-strong'"
              @click="emit('select', i)"
            >
              <span class="h-9 w-14 shrink-0 rounded-lg bg-cover bg-center" :style="thumb(i)" aria-hidden="true" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ s.name }}</span>
                <span class="block truncate text-[11px] text-ink-subtle">{{ s.title }} · {{ s.sub }}</span>
              </span>
              <span v-if="active === i" class="flex shrink-0 items-center gap-1 rounded-full bg-brand px-2.5 py-1 text-[11px] text-white">
                <IconCheck class="size-3.5" aria-hidden="true" /> On air
              </span>
              <span v-else class="shrink-0 rounded-full px-2.5 py-1 text-[11px] text-ink-subtle ring-1 ring-line">Publish</span>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </figure>
</template>
