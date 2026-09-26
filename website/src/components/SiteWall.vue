<script setup lang="ts">
/**
 * The screen wall under "Turn your screen into a billboard": landscape screens set around a
 * cylinder that turns slowly, so the one in front faces you and the rest curve away to the sides
 * (the far half is hidden), and under them the CMS. Every few seconds the CMS picks the next
 * piece of content and publishes it; the button fills as it goes out, and every screen on the
 * wall changes to it, in a quick wave along each row.
 *
 * The loop runs only while the wall is on screen, and not at all for a visitor who asked for
 * less motion: they get the wall standing still, showing the first piece.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import IconCheck from '~icons/material-symbols/check-circle'
import IconUpload from '~icons/material-symbols/upload'

import mark from '@/assets/marien-mark.png'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const SLIDES = ['welcome', 'menu', 'promo', 'townhall'].map((n) => `/shots/wall/${n}.webp`)
/** Screens around the ring; the spacing in style.css (.ring3d) is worked out for ten. */
const SCREENS = 10
const SEND_MS = 900
const PERIOD_MS = 4800

type State = 'idle' | 'sending' | 'done'
const state = ref<State>('idle')
/** What the screens are showing, and what the CMS has picked to send next. */
const live = ref(0)
const picked = ref(1)
const items = computed(() => m.value.wall.items.map((name, i) => ({ name, src: SLIDES[i] })))

const root = ref<HTMLElement>()
const timers: number[] = []
let loop: number | undefined

function cycle() {
  picked.value = (live.value + 1) % SLIDES.length
  timers.push(window.setTimeout(() => { state.value = 'sending' }, 900))
  timers.push(window.setTimeout(() => { live.value = picked.value; state.value = 'done' }, 900 + SEND_MS))
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
  const io = new IntersectionObserver(([e]) => { turning.value = e.isIntersecting; if (e.isIntersecting) start(); else stop() }, { threshold: 0.25 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => io.disconnect())
})
onBeforeUnmount(stop)

/** Each screen's place on the ring, and its turn in the wave when a change lands. */
const RING = Array.from({ length: SCREENS }, (_, i) => ({ key: i, wave: i * 50 }))
/** The ring only turns while the wall is on screen. */
const turning = ref(false)
</script>

<template>
  <div ref="root" class="mt-10 sm:mt-14" aria-hidden="true">
    <!-- The ring, out to the window's edges (100vw includes a scrollbar, so overflow-x-clip on
         <main> keeps that from adding a sideways scroll). -->
    <div class="ring3d-stage relative left-1/2 w-screen -translate-x-1/2 overflow-hidden pb-10 pt-4">
      <div class="ring3d" :class="!turning && 'ring3d-paused'">
        <div v-for="s in RING" :key="s.key" class="ring3d-item" :style="{ '--i': s.key }">
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

    <!-- The CMS, under the wall. -->
    <div class="relative mx-auto mt-2 max-w-3xl overflow-hidden rounded-2xl bg-white shadow-[0_30px_80px_-30px_rgba(0,24,77,0.5)] ring-1 ring-line sm:mt-12">
      <div class="flex items-center gap-1.5 border-b border-line bg-surface px-4 py-2.5">
        <span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" />
        <span class="ml-3 truncate rounded bg-white px-2.5 py-0.5 text-xs text-ink-muted ring-1 ring-line">app.marien.co.id</span>
      </div>
      <div class="p-5 sm:p-7">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <img :src="mark" alt="" class="size-6" />
            <span class="display text-lg text-ink sm:text-xl">{{ m.wall.account }}</span>
          </div>
          <span class="flex items-center gap-1.5 text-sm text-ink-muted"><span class="size-2 rounded-full bg-emerald-500" />{{ m.wall.screens }}</span>
        </div>

        <ul class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <li
            v-for="(it, i) in items" :key="it.src"
            class="overflow-hidden rounded-lg ring-2 transition-colors duration-300"
            :class="i === picked && state !== 'idle' ? 'ring-brand' : i === picked ? 'ring-brand/60' : 'ring-transparent'"
          >
            <img :src="it.src" alt="" class="block aspect-video w-full object-cover" loading="lazy" decoding="async" />
            <p class="flex items-center justify-between gap-1 bg-surface px-2.5 py-1.5 text-xs text-ink">
              <span class="truncate">{{ it.name }}</span>
              <span v-if="i === live" class="size-1.5 shrink-0 rounded-full bg-emerald-500" />
            </p>
          </li>
        </ul>

        <!-- The press, filling as the change goes out. -->
        <div
          class="relative mt-5 overflow-hidden rounded-lg py-3 text-center text-sm font-medium text-white transition-colors duration-300"
          :class="state === 'done' ? 'bg-emerald-600' : 'bg-action'"
        >
          <div
            class="absolute inset-0 origin-left bg-brand-bright"
            :class="state === 'sending' ? 'scale-x-100 transition-transform duration-[900ms] ease-out' : 'scale-x-0 transition-none'"
          />
          <span class="relative inline-flex items-center gap-2">
            <IconCheck v-if="state === 'done'" class="size-5" />
            <IconUpload v-else class="size-5" />
            {{ state === 'idle' ? m.wall.publish : state === 'sending' ? m.wall.publishing : m.wall.live }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
