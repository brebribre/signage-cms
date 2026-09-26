<script setup lang="ts">
/**
 * Publishing, animated, as a product shot: a signage totem standing beside the CMS window.
 * The CMS picks the next playlist and publishes it; the button fills as it goes out, a bar runs
 * along the foot of the totem's screen as it downloads, and the new content pushes the old one
 * off. The window runs off the scene's right and bottom
 * edges, so the pair reads as a crop of a bigger scene rather than two boxes side by side.
 *
 * In the hero it plays the Nusantara Tower showcase, the building the screenshots and demo
 * videos come from; in the Publish card, the site's own drawn slides.
 *
 * It brings no background of its own: it stands on whatever sweep its host draws behind it (the
 * Publish card's, or the hero's on a phone).
 *
 * Every length inside the panel is in container units, so the whole picture scales as one at
 * any width, phone included.
 *
 * The loop only runs while the scene is on screen, and not at all for a visitor who asked
 * for less motion, who gets the finished state instead.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import IconCheck from '~icons/material-symbols/check-circle'
import IconUpload from '~icons/material-symbols/upload'

import mark from '@/assets/marien-mark.png'
import SlideArt from './SlideArt.vue'
import { SLIDE_COUNT, useSlides } from '@/data/slides'
import { NUSANTARA } from '@/data/nusantara'
import { useI18n } from '@/i18n'

/** In the hero, from tablet width up, the totem stands flush with the headline's left edge and the CMS
 *  window runs on past the scene, off the page's right edge. Elsewhere it keeps inside the scene. */
const props = defineProps<{ hero?: boolean }>()
const { m } = useI18n()
const slides = useSlides()
/** The one screen the picture publishes to. */
const screen = computed(() => (props.hero ? NUSANTARA.screen : m.value.publish.screens[0]))
const campaign = computed(() => (props.hero ? NUSANTARA.campaign : m.value.hero.campaign))
/** What it plays: in the hero, the showcase building's real slides; elsewhere, the drawn ones. */
const items = computed<{ name: string; src?: string }[]>(() => (props.hero ? NUSANTARA.slides : slides.value))
const SEND_MS = 800
const SYNC_MS = 900
const PERIOD_MS = 5200

type State = 'idle' | 'sending' | 'syncing' | 'done'
const state = ref<State>('idle')
/** What the screens are playing, and what the card is about to send. */
const live = ref(0)
const next = () => (live.value + 1) % SLIDE_COUNT
const outgoing = ref(next())
const root = ref<HTMLElement>()
const timers: number[] = []
let loop: number | undefined

function press() {
  outgoing.value = next()
  state.value = 'sending'
  timers.push(window.setTimeout(() => { state.value = 'syncing' }, SEND_MS))
  // The slide changes as the screen's download bar fills.
  timers.push(window.setTimeout(() => { live.value = outgoing.value; state.value = 'done' }, SEND_MS + SYNC_MS))
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
  // Fetch every slide now, so each one is there the moment it goes on air.
  items.value.forEach((s) => { if (s.src) new Image().src = s.src })
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { state.value = 'done'; return }
  const io = new IntersectionObserver(([e]) => (e.isIntersecting ? start() : stop()), { threshold: 0.3 })
  if (root.value) io.observe(root.value)
  onBeforeUnmount(() => io.disconnect())
})
onBeforeUnmount(stop)

</script>

<template>
  <div ref="root" class="@container relative aspect-[1/0.9] overflow-hidden" :class="props.hero && 'sm:overflow-visible'" aria-hidden="true">
    <!-- The CMS window, beside the totem with a clear gap between them, running off the right
         edge. In the hero, from tablet width up, the window runs on under the hero's second wave
         while what's in it keeps its usual width. -->
    <div
      class="absolute bottom-[-6%] left-[50%] top-[16%] w-[64%] overflow-hidden rounded-tl-[3cqw] bg-white shadow-[0_30px_80px_-30px_rgba(0,24,77,0.55)] ring-1 ring-line"
      :class="props.hero && 'sm:left-[46%] sm:w-[170%]'"
    >
      <div class="flex items-center gap-[1.2cqw] border-b border-line bg-surface px-[3cqw] py-[2cqw]">
        <span class="size-[1.8cqw] rounded-full bg-line-strong" /><span class="size-[1.8cqw] rounded-full bg-line-strong" /><span class="size-[1.8cqw] rounded-full bg-line-strong" />
      </div>
      <div class="py-[4cqw] pl-[8cqw] pr-[4cqw]" :class="props.hero && 'sm:max-w-[64cqw]'">
        <div class="flex items-center gap-[2cqw]">
          <img :src="mark" alt="" class="h-[4cqw] w-auto" />
          <span class="display truncate text-[3.6cqw] text-ink">{{ campaign }}</span>
        </div>
        <p class="mt-[3cqw] flex items-center gap-[1.2cqw] text-[2.4cqw] text-ink-subtle">
          <span class="size-[1.4cqw] rounded-full bg-emerald-500" /> {{ screen.name }} · {{ screen.kind }}
        </p>

        <ul class="mt-[3cqw] divide-y divide-line overflow-hidden rounded-[2cqw] ring-1 ring-line">
          <li
            v-for="(s, i) in items" :key="i"
            class="flex items-center gap-[2cqw] px-[2.5cqw] py-[1.8cqw] transition-colors duration-300"
            :class="i === outgoing ? 'bg-brand-soft' : 'bg-white'"
          >
            <span
              class="flex size-[2.6cqw] shrink-0 items-center justify-center rounded-full ring-1 transition-colors duration-300"
              :class="i === outgoing ? 'ring-brand' : 'ring-line-strong'"
            ><span v-if="i === outgoing" class="size-[1.4cqw] rounded-full bg-brand" /></span>
            <span class="h-[4.5cqw] w-[7cqw] shrink-0 overflow-hidden rounded-[1cqw] ring-1 ring-line"><img v-if="s.src" :src="s.src" alt="" class="size-full object-cover" /><SlideArt v-else :slide="slides[i]" thumb /></span>
            <span class="min-w-0 truncate text-[2.8cqw] text-ink">{{ s.name }}</span>
            <span v-if="i === live" class="shrink-0 rounded-full bg-emerald-50 px-[1.6cqw] py-[0.4cqw] text-[2.1cqw] text-emerald-700">On air</span>
          </li>
        </ul>

        <p class="mt-[3cqw] truncate text-[2.4cqw] text-ink-muted">
          {{ state === 'idle' ? m.publish.ready : state === 'done' ? m.publish.live : m.publish.sending }}
        </p>
        <!-- The press, filling as the change goes out. -->
        <div
          class="relative mt-[1.5cqw] overflow-hidden rounded-[2cqw] py-[2.4cqw] text-center text-[2.8cqw] font-medium text-white transition-colors duration-300"
          :class="state === 'done' ? 'bg-emerald-600' : 'bg-brand-deep'"
        >
          <div
            class="absolute inset-0 origin-left bg-brand-bright"
            :class="state === 'sending' || state === 'syncing' ? 'scale-x-100 transition-transform duration-[800ms] ease-out' : 'scale-x-0 transition-none'"
          />
          <span class="relative inline-flex items-center gap-[1.2cqw]">
            <IconCheck v-if="state === 'done'" class="size-[3cqw]" />
            <IconUpload v-else class="size-[3cqw]" />
            {{ state === 'idle' ? m.publish.button : state === 'done' ? m.publish.published : m.publish.publishing }}
          </span>
        </div>
      </div>
    </div>

    <!-- The totem, in front: a screen in a black bezel with softly squared corners, the
         way a real display panel is, on a rectangular base. -->
    <div class="absolute left-[5%] top-[10%] w-[38%]" :class="props.hero && 'sm:left-0'">
      <div class="rounded-t-[1.8cqw] bg-gradient-to-b from-[#1b1e24] to-[#0f1115] p-[1.6cqw] shadow-[0_40px_60px_-30px_rgba(0,24,77,0.6),inset_0_1px_0_rgba(255,255,255,0.12)] ring-1 ring-black/60">
        <div class="relative aspect-[9/15] overflow-hidden bg-brand-deep shadow-[0_0_0_1px_rgba(0,24,77,0.12)]">
          <Transition name="swap">
            <div :key="live" class="absolute inset-0">
              <img v-if="items[live].src" :src="items[live].src" alt="" class="size-full object-cover" />
              <SlideArt v-else :slide="slides[live]" />
            </div>
          </Transition>
          <!-- The download: a bar along the foot of the screen, then gone. -->
          <div class="absolute inset-x-0 bottom-0 h-[1cqw] bg-white/15">
            <div
              class="h-full origin-left bg-accent"
              :class="{
                'scale-x-0 opacity-0': state === 'idle' || state === 'sending',
                'scale-x-100 opacity-100 transition-transform duration-[900ms] ease-out': state === 'syncing',
                'scale-x-100 opacity-0 transition-opacity duration-500': state === 'done',
              }"
            />
          </div>
        </div>
      </div>
      <!-- The base: a tall rectangular block under the screen, as wide as the bezel, so screen
           and base read as one floor-standing totem, in the bezel's own finish. It runs on past
           the foot of the scene (and of the hero), as the CMS window does, so the totem is cut
           by the edge rather than ending just short of it. -->
      <div class="h-[40cqw] w-full bg-gradient-to-b from-[#0f1115] via-[#1b1e24] to-[#14161b] shadow-[0_24px_34px_-20px_rgba(0,24,77,0.6),inset_0_1px_0_rgba(255,255,255,0.08)] ring-1 ring-black/60" />
    </div>
  </div>
</template>
