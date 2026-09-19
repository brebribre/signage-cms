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
import IconCheck from '~icons/material-symbols/check'

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
  <!-- The dark stretch, entered on a diagonal: the change of pace between designing the
       content and it being on the wall. -->
  <section id="publish" ref="root" class="angled-band angled-band-up relative -mt-[7vw] text-ink-inverse">
    <div class="relative mx-auto max-w-5xl px-5 pt-[calc(7vw+5rem)] pb-24 sm:px-8 sm:pb-28">
      <div class="reveal mx-auto max-w-2xl text-center">
        <p class="text-[13px] font-medium uppercase tracking-wider text-white/70">Publish</p>
        <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">Publish them effortlessly.</h2>
        <p class="mt-4 text-white/80">One press. Every screen, in seconds.</p>
      </div>

      <div class="reveal mx-auto mt-14 max-w-2xl">
        <!-- The press. -->
        <div class="mx-auto w-full max-w-sm rounded-2xl border border-white/15 bg-white/8 p-3 backdrop-blur">
          <div class="flex items-center gap-3">
            <span
              class="size-9 shrink-0 rounded-lg"
              :style="{ background: `linear-gradient(135deg, ${card().from}, ${card().to})` }"
              aria-hidden="true"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm text-white">{{ card().name }}</span>
              <span class="block text-[11px] text-white/55">3 screens</span>
            </span>
            <span
              class="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs transition-all duration-200"
              :class="{
                'bg-white text-brand': state === 'idle',
                'scale-95 bg-white/85 text-brand': state === 'sending',
                'bg-emerald-400/20 text-emerald-200': state === 'done',
              }"
            >
              <IconCheck v-if="state === 'done'" class="size-3.5" aria-hidden="true" />
              {{ state === 'sending' ? 'Publishing' : state === 'done' ? 'Published' : 'Publish' }}
            </span>
          </div>
        </div>

        <!-- The wire. The faint paths are always there; the bright ones run on each press. -->
        <svg class="h-16 w-full sm:h-20" viewBox="0 0 300 80" preserveAspectRatio="none" aria-hidden="true">
          <g fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="1" stroke-dasharray="4 4">
            <path d="M150 0 V34" /><path d="M50 34 H250" />
            <path d="M50 34 V80" /><path d="M150 34 V80" /><path d="M250 34 V80" />
          </g>
          <g :key="pulse" fill="none" stroke="#7fe7ff" stroke-width="2" stroke-linecap="round">
            <path class="pulse-path" style="--dur: 0.45s" pathLength="100" d="M150 0 V34" />
            <path class="pulse-path" style="--dur: 0.4s; --delay: 0.35s" pathLength="100" d="M150 34 H50" />
            <path class="pulse-path" style="--dur: 0.4s; --delay: 0.35s" pathLength="100" d="M150 34 H250" />
            <path class="pulse-path" style="--dur: 0.35s; --delay: 0.7s" pathLength="100" d="M50 34 V80" />
            <path class="pulse-path" style="--dur: 0.35s; --delay: 0.55s" pathLength="100" d="M150 34 V80" />
            <path class="pulse-path" style="--dur: 0.35s; --delay: 0.7s" pathLength="100" d="M250 34 V80" />
          </g>
        </svg>

        <!-- The screens, changing on a stagger. -->
        <ul class="grid grid-cols-3 gap-3 sm:gap-5">
          <li
            v-for="(name, idx) in SCREENS" :key="name"
            class="rounded-2xl border border-white/12 bg-white/6 p-2.5 backdrop-blur sm:p-3"
          >
            <!-- The new content pushes the old one off the top, rather than fading through it:
                 two sets of words dissolving over each other reads as a glitch, not a change.
                 Each screen is a little later than the last, the way a fleet actually updates. -->
            <div class="relative h-16 overflow-hidden rounded-lg sm:h-20" :style="{ '--swap-delay': `${idx * 160}ms` }">
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
            <p class="mt-2.5 truncate text-[11px] text-white/85 sm:text-sm">{{ name }}</p>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
