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
import FeatureCard from './FeatureCard.vue'

const TABS = [
  {
    n: '1', label: 'Design', chrome: 'paskall · Scene', src: '/shots/scene.webp',
    title: 'Design your content.',
    text: 'Photos, video, live websites and text on one canvas, at the screen’s real shape.',
  },
  {
    n: '2', label: 'Playlist', chrome: 'paskall · Playlist', src: '/shots/playlist.webp',
    title: 'Play them in order.',
    text: 'Put your designs in the order they should run, and set how long each one holds. They play one after another.',
  },
  {
    n: '3', label: 'Schedule', chrome: 'paskall · Campaign', src: '/shots/campaign.webp',
    title: 'Say where and when.',
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
  <section id="design" ref="root">
    <FeatureCard tone="sky" tag="Content" reverse>
      <template #visual>
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
      </template>

      <!-- The step's own headline and line, above the pills that choose it. Held to a minimum
           height so a shorter step does not shuffle the card as it comes round. -->
      <div class="mt-5 min-h-[12rem] sm:min-h-[10rem]">
        <Transition name="fade" mode="out-in">
          <div :key="active">
            <h2 class="text-4xl leading-[1.1] sm:text-5xl">{{ TABS[active].title }}</h2>
            <p class="mt-5 max-w-md leading-relaxed text-ink-muted">{{ TABS[active].text }}</p>
          </div>
        </Transition>
      </div>

      <div class="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="The editor">
        <button
          v-for="(t, i) in TABS" :key="t.label"
          type="button" role="tab" :aria-selected="active === i"
          class="relative inline-flex items-center gap-2 overflow-hidden rounded-full py-1.5 pl-1.5 pr-4 text-sm ring-1 transition-colors"
          :class="active === i ? 'bg-brand-deep text-white ring-brand-deep' : 'bg-white text-ink ring-line hover:ring-line-strong'"
          @click="choose(i)"
        >
          <span
            class="inline-flex size-6 items-center justify-center rounded-full text-[11px] font-semibold"
            :class="active === i ? 'bg-accent text-brand-deep' : 'bg-sky-strong text-brand-deep'"
          >{{ t.n }}</span>
          {{ t.label }}
          <!-- How long this tab has left, drawn rather than guessed at. Re-keyed so the bar
               restarts with the tab rather than carrying on from wherever it was. -->
          <span
            v-if="auto && active === i" :key="active"
            class="tab-progress absolute inset-x-0 bottom-0 h-0.5 origin-left bg-accent"
          />
        </button>
      </div>
    </FeatureCard>
  </section>
</template>
