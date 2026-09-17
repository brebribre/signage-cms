<script setup lang="ts">
/** The media itself and nothing else — a gallery tile, not a record. Square corners so a grid
 *  of them reads as one wall of content rather than a stack of cards; the only overlay is a
 *  play mark on videos, since a still frame alone can't say it moves. The filename survives
 *  only as alt/hover text. Presentational only: handed a URL, knows nothing about uploads.
 *
 *  `selectable` turns the tile into a checkbox (the Media page's select mode): a round tick in
 *  the corner, and a brand outline and wash once chosen. A button either way, so it is
 *  reachable and operable from the keyboard. */
import IconCheck from '~icons/material-symbols/check'
import IconPlayArrow from '~icons/material-symbols/play-arrow'

withDefaults(
  defineProps<{
    filename: string
    kind: 'image' | 'video'
    thumbnailUrl: string | null
    selectable?: boolean
    selected?: boolean
  }>(),
  { selectable: false, selected: false },
)
</script>

<template>
  <button
    type="button"
    class="relative block w-full cursor-pointer overflow-hidden bg-raised transition-opacity duration-200
           ease-[cubic-bezier(0.4,0,0.2,1)] focus-visible:z-10 focus-visible:outline-2
           focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
    :class="!selectable && 'hover:opacity-85'"
    :title="filename"
    :role="selectable ? 'checkbox' : undefined"
    :aria-checked="selectable ? selected : undefined"
    :aria-label="filename"
  >
    <!-- Height from a width-relative spacer, not aspect-ratio: see MediaPicker.vue. -->
    <span class="block pt-[100%]" aria-hidden="true" />
    <img
      v-if="thumbnailUrl"
      :src="thumbnailUrl"
      :alt="filename"
      class="absolute inset-0 size-full object-cover"
      loading="lazy"
    />
    <span
      v-if="kind === 'video'"
      class="absolute top-1.5 left-1.5 flex size-6 items-center justify-center bg-ink/70 text-ink-inverse"
      aria-hidden="true"
    >
      <IconPlayArrow class="size-4" />
    </span>

    <template v-if="selectable">
      <span
        v-if="selected"
        class="absolute inset-0 bg-brand/25 ring-3 ring-brand ring-inset"
        aria-hidden="true"
      />
      <span
        class="absolute top-1.5 right-1.5 flex size-6 items-center justify-center rounded-full border-2
               transition-colors duration-150"
        :class="selected ? 'border-brand bg-brand text-ink-inverse' : 'border-white bg-ink/25 text-transparent'"
        aria-hidden="true"
      >
        <IconCheck class="size-4" />
      </span>
    </template>
  </button>
</template>
