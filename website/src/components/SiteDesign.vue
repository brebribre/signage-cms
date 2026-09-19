<script setup lang="ts">
/**
 * The editor, shown rather than described: four tabs that turn over on their own, so a visitor
 * who does nothing still sees all of it. Clicking a tab takes the wheel for good, because an
 * auto-playing tour that overrides the person watching it is worse than no tour.
 *
 * All four shots are in the DOM and cross fade on opacity, so switching never shows a gap
 * while an image decodes.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import BrowserFrame from './BrowserFrame.vue'

const TABS = [
  {
    n: '1', label: 'Design', chrome: 'paskall · Scene', src: '/shots/scene.webp',
    text: 'Photos, video, live websites and text on one canvas, at the screen’s real shape.',
  },
  {
    n: '2', label: 'Playlist', chrome: 'paskall · Playlist', src: '/shots/playlist.webp',
    text: 'Put your designs in the order they should run, and set how long each one holds. They play one after another.',
  },
  {
    n: '3', label: 'Schedule', chrome: 'paskall · Campaign', src: '/shots/campaign.webp',
    text: 'Choose the screens and the hours. One loop all day, or different content by time and weekday.',
  },
]
const DWELL_MS = 4000

const active = ref(0)
const auto = ref(true)
const root = ref<HTMLElement>()
let timer: number | undefined

function stop() {
  if (timer) { clearInterval(timer); timer = undefined }
}
function start() {
  if (timer || !auto.value) return
  timer = window.setInterval(() => { active.value = (active.value + 1) % TABS.length }, DWELL_MS)
}
function choose(i: number) {
  active.value = i
  auto.value = false
  stop()
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { auto.value = false; return }
  // Only turn over while the section is on screen: a tour nobody is looking at should not be
  // running, and the tab that is showing when a visitor arrives should be the first one.
  const io = new IntersectionObserver(([e]) => (e.isIntersecting ? start() : stop()), { threshold: 0.25 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => { io.disconnect(); stop() })
})
onBeforeUnmount(stop)
</script>

<template>
  <section id="design" ref="root" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="grid gap-10 lg:grid-cols-12 lg:gap-12">
      <div class="lg:col-span-5">
        <div class="lg:sticky lg:top-28">
          <p class="reveal text-[13px] font-medium uppercase tracking-wider text-brand">Content</p>
          <h2 class="reveal mt-3 text-3xl leading-tight sm:text-4xl">Design your content.</h2>

          <div class="reveal mt-7 flex flex-wrap gap-2" role="tablist" aria-label="The editor">
            <button
              v-for="(t, i) in TABS" :key="t.label"
              type="button" role="tab" :aria-selected="active === i"
              class="relative inline-flex items-center gap-2 overflow-hidden rounded-full border py-1.5 pl-1.5 pr-4 text-sm transition-colors"
              :class="active === i ? 'border-brand bg-brand-soft text-brand' : 'border-line text-ink-muted hover:border-line-strong hover:text-ink'"
              @click="choose(i)"
            >
              <span
                class="inline-flex size-5 items-center justify-center rounded-full text-[11px]"
                :class="active === i ? 'bg-brand text-white' : 'bg-raised text-ink-subtle'"
              >{{ t.n }}</span>
              {{ t.label }}
              <!-- How long this tab has left, drawn rather than guessed at. Re-keyed so the bar
                   restarts with the tab rather than carrying on from wherever it was. -->
              <span
                v-if="auto && active === i" :key="active"
                class="tab-progress absolute inset-x-0 bottom-0 h-0.5 origin-left bg-brand"
              />
            </button>
          </div>

          <p class="reveal mt-5 min-h-[4.5rem] leading-relaxed text-ink-muted">{{ TABS[active].text }}</p>
        </div>
      </div>

      <div class="reveal lg:col-span-7">
        <BrowserFrame :label="TABS[active].chrome">
          <div class="relative aspect-[1.6] w-full bg-page">
            <img
              v-for="(t, i) in TABS" :key="t.label"
              :src="t.src" :alt="`${t.label} in Paskall`"
              class="absolute inset-0 size-full object-cover transition-opacity duration-500"
              :class="active === i ? 'opacity-100' : 'opacity-0'"
              loading="lazy" decoding="async"
            />
          </div>
        </BrowserFrame>
      </div>
    </div>
  </section>
</template>
