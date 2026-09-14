<script setup lang="ts">
/** The media itself and nothing else — a gallery tile, not a record. Square corners so a grid
 *  of them reads as one wall of content rather than a stack of cards; the only overlay is a
 *  play mark on videos, since a still frame alone can't say it moves. The filename survives
 *  only as alt/hover text. Presentational only: handed a URL, knows nothing about uploads. */
import IconPlayArrow from '~icons/material-symbols/play-arrow'

defineProps<{
  filename: string
  kind: 'image' | 'video'
  thumbnailUrl: string | null
}>()
</script>

<template>
  <div
    class="relative aspect-video w-full cursor-pointer overflow-hidden bg-raised transition-opacity
           duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] hover:opacity-85"
    :title="filename"
  >
    <img
      v-if="thumbnailUrl"
      :src="thumbnailUrl"
      :alt="filename"
      class="size-full object-cover"
      loading="lazy"
    />
    <span
      v-if="kind === 'video'"
      class="absolute top-1.5 left-1.5 flex size-6 items-center justify-center bg-ink/70 text-ink-inverse"
      aria-label="Video"
    >
      <IconPlayArrow class="size-4" />
    </span>
  </div>
</template>
