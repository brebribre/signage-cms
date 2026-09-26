<script setup lang="ts">
/**
 * The editor, shown rather than described: three steps that turn over on their own, so a
 * visitor who does nothing still sees all of it, with a row of small bars under the words that
 * says which step is showing and how long it has left. Clicking a bar takes the wheel for good,
 * because an auto-playing tour that overrides the person watching it is worse than no tour.
 *
 * All three shots are in the DOM and cross fade on opacity, so switching never shows a gap
 * while an image decodes.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import BrowserFrame from './BrowserFrame.vue'
import FeatureCard from './FeatureCard.vue'
import { SECONDARY } from '@/data/buttons'
import { useI18n } from '@/i18n'

/** The shots and their window titles are the CMS's own, in English; the words are the page's. */
const SHOTS = [
  { n: '1', chrome: 'paskall · Scene', src: '/shots/scene.webp' },
  { n: '2', chrome: 'paskall · Playlist', src: '/shots/playlist.webp' },
  { n: '3', chrome: 'paskall · Campaign', src: '/shots/campaign.webp' },
]
const { m } = useI18n()
const TABS = computed(() => SHOTS.map((s, i) => ({ ...s, ...m.value.design.tabs[i] })))
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
  timer = window.setInterval(() => { active.value = (active.value + 1) % SHOTS.length }, DWELL_MS)
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
    <FeatureCard pattern="sweep">
      <!-- The step's own title and line. Held to a minimum height so a shorter step does not
           shuffle the card as it comes round. -->
      <div class="min-h-[7.5rem] sm:min-h-[8.5rem]">
        <Transition name="fade" mode="out-in">
          <div :key="active">
            <h3 class="text-3xl leading-[1.1] sm:text-4xl">{{ TABS[active].title }}</h3>
            <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ TABS[active].text }}</p>
          </div>
        </Transition>
      </div>

      <div class="mt-4 flex items-center gap-1" role="tablist" :aria-label="m.design.tablist">
        <button
          v-for="(t, i) in TABS" :key="t.n"
          type="button" role="tab" :aria-selected="active === i" :aria-label="t.label"
          class="group py-2 pr-1"
          @click="choose(i)"
        >
          <span
            class="relative block h-1.5 overflow-hidden rounded-full transition-all duration-300"
            :class="active === i ? 'w-10 bg-brand-deep/15' : 'w-1.5 bg-line-strong group-hover:bg-ink-subtle'"
          >
            <!-- How long this step has left, drawn rather than guessed at. Re-keyed so the bar
                 restarts with the step rather than carrying on from wherever it was. -->
            <span
              v-if="active === i" :key="active"
              class="absolute inset-0 origin-left rounded-full bg-brand-deep"
              :class="auto && 'tab-progress'"
            />
          </span>
        </button>
      </div>

      <!-- Every feature, each on a card of its own like this one. -->
      <a href="/features" :class="SECONDARY" class="mt-5 inline-flex items-center gap-2 px-5 py-2.5 text-sm">
        {{ m.design.seeAll }} <IconArrowForward class="size-4" />
      </a>

      <template #visual>
        <!-- Running off the card's right and bottom edges. -->
        <BrowserFrame :label="TABS[active].chrome" class="rounded-tl-xl border-r-0 border-b-0">
          <div class="relative aspect-[16/9] w-full bg-page">
            <img
              v-for="(t, i) in TABS" :key="t.n"
              :src="t.src" :alt="`${t.label} ${m.design.inPaskall}`"
              class="absolute inset-0 size-full object-cover object-left-top transition-opacity duration-500"
              :class="active === i ? 'opacity-100' : 'opacity-0'"
              loading="lazy" decoding="async"
            />
          </div>
        </BrowserFrame>
      </template>
    </FeatureCard>
  </section>
</template>
