<script setup lang="ts">
/**
 * The screen wall under "Publish to your entire fleet at once": a row of landscape screens
 * drifting slowly past. Every few seconds a new piece of content is published: a small
 * notification under the ring says it's going out, then that it's live, sending a wave out to the
 * ring, and every screen changes to it as the wave reaches it.
 *
 * The loop runs only while the wall is on screen, and not at all for a visitor who asked for
 * less motion: they get the wall standing still, showing the first piece.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconCheck from '~icons/material-symbols/check-circle'
import IconUpload from '~icons/material-symbols/upload'

import { useI18n } from '@/i18n'

const { m } = useI18n()
const SLIDES = ['welcome', 'menu', 'promo', 'townhall'].map((n) => `/shots/wall/${n}.webp`)
const SCREENS = 6
const SEND_MS = 900
const PERIOD_MS = 4800

type State = 'idle' | 'sending' | 'done'
const state = ref<State>('idle')
/** What the screens are showing, what is on its way to them, and how many changes have landed
 *  (each one sends a new wave out of the notification). */
const live = ref(0)
const picked = ref(1)
const landed = ref(0)

const root = ref<HTMLElement>()
const timers: number[] = []
let loop: number | undefined

function cycle() {
  picked.value = (live.value + 1) % SLIDES.length
  timers.push(window.setTimeout(() => { state.value = 'sending' }, 900))
  timers.push(window.setTimeout(() => { live.value = picked.value; landed.value++; state.value = 'done' }, 900 + SEND_MS))
  timers.push(window.setTimeout(() => { state.value = 'idle' }, PERIOD_MS - 300))
}
function start() {
  if (loop) return
  timers.push(window.setTimeout(cycle, 500))
  loop = window.setInterval(cycle, PERIOD_MS)
}
function stop() {
  if (loop) { clearInterval(loop); loop = undefined }
  timers.splice(0).forEach(clearTimeout)
}
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const io = new IntersectionObserver(([e]) => (e.isIntersecting ? start() : stop()), { threshold: 0.25 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => io.disconnect())
})
onBeforeUnmount(stop)

/** One row, its screens twice over so the drift loops with no seam; each screen's turn in the
 *  wave when a change lands. */
const ROW = Array.from({ length: SCREENS * 2 }, (_, i) => ({ key: i, wave: 350 + (i % SCREENS) * 60 }))
</script>

<template>
  <div ref="root" class="mt-10 sm:mt-14" aria-hidden="true">
    <!-- The wall, out to the window's edges (100vw includes a scrollbar, so overflow-x-clip on
         <main> keeps that from adding a sideways scroll). -->
    <div class="relative z-10 left-1/2 w-screen -translate-x-1/2 overflow-hidden pb-10 pt-2">
      <div class="wall-left flex w-max gap-5 sm:gap-6">
        <div v-for="s in ROW" :key="s.key" class="w-56 shrink-0 sm:w-72 lg:w-80">
          <div class="rounded-md bg-[#0f1115] p-1 shadow-[0_18px_30px_-18px_rgba(0,24,77,0.6)] sm:p-1.5">
            <div class="relative aspect-video overflow-hidden rounded-[3px] bg-[#0b1a4a]">
              <img
                v-for="(src, i) in SLIDES" :key="src" :src="src" alt=""
                class="absolute inset-0 size-full object-cover transition-opacity duration-500"
                :class="i === live ? 'opacity-100' : 'opacity-0'"
                :style="{ transitionDelay: `${s.wave}ms` }"
                loading="lazy" decoding="async"
              />
              <!-- The download, a bar along the foot while the change goes out. -->
              <div class="absolute inset-x-0 bottom-0 h-0.5 bg-white/10">
                <div
                  class="h-full origin-left bg-accent"
                  :class="state === 'sending' ? 'scale-x-100 opacity-100 transition-transform duration-[900ms] ease-out' : state === 'done' ? 'scale-x-100 opacity-0 transition-opacity duration-500' : 'scale-x-0 opacity-0'"
                />
              </div>
            </div>
          </div>
          <div class="mx-auto h-1.5 w-1/4 rounded-b bg-[#0f1115]" />
        </div>
      </div>
    </div>

    <!-- The notification, under the wall: what is going out, then that it's live, sending a wave
         up to the screens as it lands (restarted by its key; behind the screens). -->
    <div class="relative flex h-20 justify-center">
      <!-- Only the upper half: the wave goes up, toward the screens. -->
      <div class="pointer-events-none absolute bottom-1/2 left-1/2 h-[26rem] w-[52rem] max-w-[100vw] -translate-x-1/2 overflow-hidden" aria-hidden="true">
        <template v-if="landed">
          <span v-for="n in 2" :key="`${landed}-${n}`" class="fleet-wave" :style="{ animationDelay: `${(n - 1) * 260}ms` }" />
        </template>
      </div>
      <Transition name="toast">
        <div v-if="state !== 'idle'" class="relative z-10 flex w-full max-w-sm items-center gap-3 rounded-2xl bg-white p-3 pr-4 shadow-[0_20px_50px_-20px_rgba(0,24,77,0.45)] ring-1 ring-line">
          <img :src="SLIDES[picked]" alt="" class="aspect-video w-16 shrink-0 rounded-md object-cover" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-ink">{{ m.wall.items[picked] }}</p>
            <p class="mt-0.5 flex items-center gap-1.5 text-xs" :class="state === 'done' ? 'text-emerald-700' : 'text-ink-muted'">
              <IconCheck v-if="state === 'done'" class="size-4" />
              <IconUpload v-else class="size-4" />
              {{ state === 'done' ? m.wall.live : m.wall.sending }}
            </p>
            <div class="mt-2 h-1 overflow-hidden rounded-full bg-line">
              <div
                class="h-full origin-left rounded-full"
                :class="state === 'done' ? 'scale-x-100 bg-emerald-500' : 'bg-brand-bright scale-x-100 transition-transform duration-[900ms] ease-out'"
              />
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>
