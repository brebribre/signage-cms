<script setup lang="ts">
/**
 * Publishing, animated: press once in the CMS, a bar fills as the change goes out, then each
 * screen downloads it in turn and swaps to the new slide. The screens are the same cards the
 * hero floats round the CMS, so the page tells one story in one visual language.
 *
 * The loop only runs while the section is on screen, and not at all for a visitor who asked
 * for less motion, who gets the finished state instead.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconArrowForward from '~icons/material-symbols/arrow-forward'
import IconCheck from '~icons/material-symbols/check-circle'
import IconUpload from '~icons/material-symbols/upload'

import FeatureCard from './FeatureCard.vue'
import ScreenCard from './ScreenCard.vue'
import { SLIDES } from '@/data/slides'

const SCREENS = [
  { name: 'Lobby TV', kind: 'Android box' },
  { name: 'Entrance', kind: 'Smart TV' },
  { name: 'Cafe', kind: 'Browser' },
]
/** How far apart the screens update, the way a fleet actually does. */
const STAGGER_MS = 220
const SEND_MS = 800
const SYNC_MS = 900
const PERIOD_MS = 5200

type State = 'idle' | 'sending' | 'syncing' | 'done'
const state = ref<State>('idle')
/** What the screens are playing, and what the card is about to send. */
const live = ref(0)
const next = () => (live.value + 1) % SLIDES.length
const outgoing = ref(next())
const root = ref<HTMLElement>()
const timers: number[] = []
let loop: number | undefined

function press() {
  outgoing.value = next()
  state.value = 'sending'
  timers.push(window.setTimeout(() => { state.value = 'syncing' }, SEND_MS))
  // The slide changes as the first bar fills; each screen's own swap is delayed by its stagger.
  timers.push(window.setTimeout(() => { live.value = outgoing.value }, SEND_MS + SYNC_MS))
  timers.push(window.setTimeout(() => { state.value = 'done' }, SEND_MS + SYNC_MS + STAGGER_MS * SCREENS.length + 300))
  timers.push(window.setTimeout(() => { state.value = 'idle'; outgoing.value = next() }, PERIOD_MS - 700))
}
function stop() {
  if (loop) { clearInterval(loop); loop = undefined }
  timers.splice(0).forEach(clearTimeout)
}
function start() {
  if (loop) return
  timers.push(window.setTimeout(press, 600))
  loop = window.setInterval(press, PERIOD_MS)
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { state.value = 'done'; return }
  const io = new IntersectionObserver(([e]) => (e.isIntersecting ? start() : stop()), { threshold: 0.3 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => io.disconnect())
})
onBeforeUnmount(stop)

const thumb = (i: number) => {
  const s = SLIDES[i]
  return s.src ? { backgroundImage: `url(${s.src})` } : { background: `linear-gradient(135deg, ${s.from}, ${s.to})` }
}
</script>

<template>
  <section id="publish" ref="root">
    <FeatureCard tone="tint" tag="Publish">
      <template #visual>
        <div class="rounded-3xl bg-white/60 p-4 ring-1 ring-white sm:p-6">
          <!-- The campaign being sent, with its progress along its foot. -->
          <div class="relative mx-auto max-w-sm overflow-hidden rounded-2xl bg-white p-3 shadow-[0_20px_50px_-28px_rgba(0,24,77,0.5)] ring-1 ring-line">
            <div class="flex items-center gap-3">
              <span class="h-10 w-14 shrink-0 rounded-lg bg-cover bg-center transition-all duration-500" :style="thumb(outgoing)" aria-hidden="true" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ SLIDES[outgoing].name }}</span>
                <span class="block text-[11px] text-ink-subtle">
                  {{ state === 'idle' ? `Ready for ${SCREENS.length} screens` : state === 'done' ? `On ${SCREENS.length} of ${SCREENS.length} screens` : `Sending to ${SCREENS.length} screens` }}
                </span>
              </span>
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs transition-colors duration-300"
                :class="state === 'done' ? 'bg-emerald-50 text-emerald-700' : state === 'idle' ? 'bg-brand-deep text-white' : 'bg-brand-soft text-brand'"
              >
                <IconCheck v-if="state === 'done'" class="size-3.5" aria-hidden="true" />
                <IconUpload v-else class="size-3.5" :class="state !== 'idle' && 'animate-pulse'" aria-hidden="true" />
                {{ state === 'idle' ? 'Publish' : state === 'done' ? 'Published' : 'Publishing' }}
              </span>
            </div>
            <div class="absolute inset-x-0 bottom-0 h-1 bg-brand-soft" aria-hidden="true">
              <div
                class="h-full origin-left bg-gradient-to-r from-brand to-brand-bright"
                :class="state === 'idle' ? 'scale-x-0 transition-none' : 'scale-x-100 transition-transform duration-[800ms] ease-out'"
              />
            </div>
          </div>

          <!-- A soft beam down to the screens, lit while the change is travelling. -->
          <div class="relative mx-auto h-10 w-px bg-brand/15" aria-hidden="true">
            <div
              class="absolute inset-x-0 top-0 h-full origin-top bg-gradient-to-b from-brand-bright to-accent transition-transform duration-500 ease-out"
              :class="state === 'sending' || state === 'syncing' ? 'scale-y-100' : 'scale-y-0'"
            />
          </div>

          <ul class="grid grid-cols-3 gap-2.5 sm:gap-4">
            <li v-for="(s, i) in SCREENS" :key="s.name">
              <ScreenCard
                :active="live" :name="s.name" :kind="s.kind"
                :delay="i * STAGGER_MS" :sync="state === 'syncing' ? 'filling' : state === 'done' ? 'done' : 'idle'"
              />
            </li>
          </ul>
        </div>
      </template>

      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Publish them effortlessly</h2>
      <p class="mt-5 max-w-md leading-relaxed text-ink-muted">
        One press, and the change runs to every screen in seconds. Each screen keeps its files, so
        it carries on playing if the internet drops and catches up when it returns.
      </p>
      <a href="#contact" class="mt-8 inline-flex items-center gap-2 rounded-full bg-brand-deep px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-brand">
        Request access <IconArrowForward class="size-4" />
      </a>
    </FeatureCard>
  </section>
</template>
