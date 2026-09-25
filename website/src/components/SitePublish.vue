<script setup lang="ts">
/**
 * Publishing, animated: press once in the CMS and the change runs down the wire to every
 * screen. The screens swap on a stagger rather than together, because that is what it looks
 * like in life and it is what makes the picture read as sending rather than cutting.
 *
 * The loop only runs while the section is on screen, and not at all for a visitor who asked
 * for less motion, who gets the finished state instead.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconArrowForward from '~icons/material-symbols/arrow-forward'
import IconCheck from '~icons/material-symbols/check'

import FeatureCard from './FeatureCard.vue'

/** Two campaigns, alternating, so every press genuinely changes what the screens show. */
const CAMPAIGNS = [
  { name: 'Welcome', title: 'Welcome', sub: 'Wifi: guest', from: '#00184d', to: '#1f55c4' },
  { name: 'Autumn menu', title: 'Autumn menu', sub: '2 for 1 until 5pm', from: '#002f96', to: '#0076dd' },
]
const SCREENS = ['Lobby TV', 'Entrance totem', 'Cafe screen']

const PERIOD_MS = 4600
const ARRIVE_MS = 1150
const RESET_MS = 3100

const cycle = ref(0)
const state = ref<'idle' | 'sending' | 'done'>('idle')
/** What the last press sent, so the card keeps naming it while it says "Published" rather
 *  than flipping to the next draft the instant the screens change. */
const pending = ref(CAMPAIGNS[1])
/** Bumped on every press, and used to re-key the pulses so their animation restarts. */
const pulse = ref(0)
const root = ref<HTMLElement>()
const timers: number[] = []
let loop: number | undefined

const live = () => cycle.value % CAMPAIGNS.length
/** The card shows the next draft while it is idle, and what is in flight while it is not. */
const card = () => (state.value === 'idle' ? CAMPAIGNS[(cycle.value + 1) % CAMPAIGNS.length] : pending.value)

function press() {
  pending.value = CAMPAIGNS[(cycle.value + 1) % CAMPAIGNS.length]
  state.value = 'sending'
  pulse.value++
  timers.push(window.setTimeout(() => { cycle.value++; state.value = 'done' }, ARRIVE_MS))
  timers.push(window.setTimeout(() => { state.value = 'idle' }, RESET_MS))
}
function stop() {
  if (loop) { clearInterval(loop); loop = undefined }
  timers.splice(0).forEach(clearTimeout)
}
function start() {
  if (loop) return
  press()
  loop = window.setInterval(press, PERIOD_MS)
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { state.value = 'done'; return }
  const io = new IntersectionObserver(([e]) => (e.isIntersecting ? start() : stop()), { threshold: 0.3 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => io.disconnect())
})
onBeforeUnmount(stop)
</script>

<template>
  <section id="publish" ref="root">
    <FeatureCard tone="tint" tag="Publish">
      <template #visual>
        <div class="rounded-3xl bg-white/70 p-4 ring-1 ring-white sm:p-6">
          <!-- The press. -->
          <div class="mx-auto w-full max-w-xs rounded-2xl bg-white p-3 shadow-[0_20px_50px_-28px_rgba(0,24,77,0.5)] ring-1 ring-line">
            <div class="flex items-center gap-3">
              <span
                class="size-9 shrink-0 rounded-lg"
                :style="{ background: `linear-gradient(135deg, ${card().from}, ${card().to})` }"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ card().name }}</span>
                <span class="block text-[11px] text-ink-subtle">3 screens</span>
              </span>
              <span
                class="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs transition-all duration-200"
                :class="{
                  'bg-brand-deep text-white': state === 'idle',
                  'scale-95 bg-brand text-white': state === 'sending',
                  'bg-emerald-100 text-emerald-700': state === 'done',
                }"
              >
                <IconCheck v-if="state === 'done'" class="size-3.5" aria-hidden="true" />
                {{ state === 'sending' ? 'Publishing' : state === 'done' ? 'Published' : 'Publish' }}
              </span>
            </div>
          </div>

          <!-- The wire. The faint paths are always there; the bright ones run on each press. -->
          <svg class="h-14 w-full sm:h-16" viewBox="0 0 300 80" preserveAspectRatio="none" aria-hidden="true">
            <g fill="none" stroke="rgba(0,51,153,0.25)" stroke-width="1" stroke-dasharray="4 4">
              <path d="M150 0 V34" /><path d="M50 34 H250" />
              <path d="M50 34 V80" /><path d="M150 34 V80" /><path d="M250 34 V80" />
            </g>
            <g :key="pulse" fill="none" stroke="#0076dd" stroke-width="2" stroke-linecap="round">
              <path class="pulse-path" style="--dur: 0.45s" pathLength="100" d="M150 0 V34" />
              <path class="pulse-path" style="--dur: 0.4s; --delay: 0.35s" pathLength="100" d="M150 34 H50" />
              <path class="pulse-path" style="--dur: 0.4s; --delay: 0.35s" pathLength="100" d="M150 34 H250" />
              <path class="pulse-path" style="--dur: 0.35s; --delay: 0.7s" pathLength="100" d="M50 34 V80" />
              <path class="pulse-path" style="--dur: 0.35s; --delay: 0.55s" pathLength="100" d="M150 34 V80" />
              <path class="pulse-path" style="--dur: 0.35s; --delay: 0.7s" pathLength="100" d="M250 34 V80" />
            </g>
          </svg>

          <!-- The screens, changing on a stagger. -->
          <ul class="grid grid-cols-3 gap-2.5 sm:gap-4">
            <li
              v-for="(name, idx) in SCREENS" :key="name"
              class="rounded-2xl bg-white p-2 shadow-[0_16px_40px_-28px_rgba(0,24,77,0.5)] ring-1 ring-line sm:p-2.5"
            >
              <!-- The new content pushes the old one off the top, rather than fading through it:
                   two sets of words dissolving over each other reads as a glitch, not a change.
                   Each screen is a little later than the last, the way a fleet actually updates. -->
              <div class="relative h-16 overflow-hidden rounded-xl sm:h-20" :style="{ '--swap-delay': `${idx * 160}ms` }">
                <Transition name="swap">
                  <span
                    :key="live()"
                    class="absolute inset-0 flex flex-col justify-center px-2.5"
                    :style="{ background: `linear-gradient(135deg, ${CAMPAIGNS[live()].from}, ${CAMPAIGNS[live()].to})` }"
                  >
                    <span class="display truncate text-[11px] text-white sm:text-sm">{{ CAMPAIGNS[live()].title }}</span>
                    <span class="truncate text-[9px] text-white/70 sm:text-[11px]">{{ CAMPAIGNS[live()].sub }}</span>
                  </span>
                </Transition>
              </div>
              <p class="mt-2 truncate px-0.5 text-[11px] text-ink sm:text-sm">{{ name }}</p>
            </li>
          </ul>
        </div>
      </template>

      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Publish them effortlessly</h2>
      <p class="mt-5 max-w-md leading-relaxed text-ink-muted">
        One press, and the change runs to every screen in seconds. Each screen keeps its files, so
        it carries on playing if the internet drops and catches up when it returns.
      </p>
      <a href="#plans" class="mt-8 inline-flex items-center gap-2 rounded-full bg-brand-deep px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-brand">
        See pricing <IconArrowForward class="size-4" />
      </a>
    </FeatureCard>
  </section>
</template>
