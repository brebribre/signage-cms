<script setup lang="ts">
/** A screen drawn as a shape — its own aspect ratio and orientation, so a row of screens reads at
 *  a glance like the wall it maps to. Not a pixel-accurate preview. Always occupies a `size`
 *  square, so a portrait screen never makes its row taller than the landscape ones around it —
 *  only what's drawn inside changes, letterboxed to fit. */
import { computed } from 'vue'

import wordmarkUrl from '@/assets/paskall-wordmark.png'
import type { DeviceRead } from '@/types/api'

const props = withDefaults(defineProps<{ device: DeviceRead; size?: number }>(), { size: 88 })

/** The device's reported resolution when it has one, else a generic ratio for its orientation,
 *  scaled to fit `size` on its longer side. Clamped so one very wide or very narrow screen can't
 *  collapse to nothing. */
const box = computed(() => {
  const d = props.device
  const ratio = d.screen_width && d.screen_height
    ? d.screen_width / d.screen_height
    : d.orientation === 'portrait' ? 9 / 16 : 16 / 9
  const clamped = Math.min(Math.max(ratio, 0.4), 2.4)
  const width = clamped >= 1 ? props.size : Math.round(props.size * clamped)
  const height = clamped >= 1 ? Math.round(props.size / clamped) : props.size
  const min = Math.round(props.size * 0.41)
  return { width: Math.max(width, min), height: Math.max(height, min) }
})

/** The bezel thins with the shape, so a small one isn't all frame. */
const bezel = computed(() => (props.size >= 72 ? 5 : 3))
</script>

<template>
  <div class="flex shrink-0 items-center justify-center" :style="{ width: `${size}px`, height: `${size}px` }">
    <div
      class="flex items-center justify-center overflow-hidden rounded-sm border-ink bg-canvas"
      :style="{
        width: `${box.width}px`,
        height: `${box.height}px`,
        borderWidth: `${bezel}px`,
        padding: `${Math.round(size * 0.09)}px ${Math.round(size * 0.14)}px`,
      }"
    >
      <!-- The logo in its own colours: a screen that belongs to this CMS. -->
      <img :src="wordmarkUrl" alt="Paskall logo" draggable="false" class="block h-full w-full select-none object-contain" />
    </div>
  </div>
</template>
