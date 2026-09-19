<script setup lang="ts">
/**
 * The hero's demo: the CMS on one side, the screen it drives on the other. It cycles on its
 * own so the page shows what it does without being touched, and stops cycling the moment
 * someone picks a playlist themselves, because taking the wheel and then being overridden is
 * the rudest thing an auto-playing demo can do.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import CmsPanel from './CmsPanel.vue'
import SignageScreen from './SignageScreen.vue'
import { SLIDES } from '@/data/slides'

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
  <!-- The panel hangs off the screen's own left edge rather than the column's, so the two keep
       their relationship at every width instead of drifting apart on a wide one. -->
  <div class="flex justify-center sm:justify-end">
    <div class="relative">
      <SignageScreen :active="active" />
      <div class="mt-4 sm:mt-0 sm:absolute sm:-bottom-6 sm:-left-40 sm:w-52 lg:-left-44 lg:w-56">
        <CmsPanel :active="active" @select="choose" />
      </div>
    </div>
  </div>
</template>
