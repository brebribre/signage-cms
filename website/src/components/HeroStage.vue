<script setup lang="ts">
/**
 * The hero's demo: the CMS on one side, the screen it drives on the other. It cycles on its
 * own so the page shows what it does without being touched, and stops cycling the moment
 * someone picks a playlist themselves, because taking the wheel and then being overridden is
 * the rudest thing an auto-playing demo can do.
 */
import { defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'

import CmsPanel from './CmsPanel.vue'
import { SLIDES } from '@/data/slides'

/** Three.js is most of this page's JavaScript, so the totem is its own chunk. */
const SignageTotem = defineAsyncComponent(() => import('./SignageTotem.vue'))

const CYCLE_MS = 3600
const active = ref(0)
let timer: number | undefined

function advance() {
  active.value = (active.value + 1) % SLIDES.length
}
function choose(i: number) {
  active.value = i
  // Hand control over for good.
  if (timer) { clearInterval(timer); timer = undefined }
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  timer = window.setInterval(advance, CYCLE_MS)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="relative">
    <SignageTotem :active="active" />
    <!-- Overlapping the totem on a wide screen, stacked beneath it on a narrow one. -->
    <div class="mt-4 sm:mt-0 sm:absolute sm:bottom-4 sm:-left-6 sm:w-52 lg:-left-16 lg:w-60">
      <CmsPanel :active="active" @select="choose" />
    </div>
  </div>
</template>
