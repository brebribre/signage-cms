<script setup lang="ts">
/** One file in the library: its picture, what it's called, and the one fact you'd look for
 *  (a video's length, a picture's size). Presentational only — handed a URL and some text, it
 *  knows nothing about uploads.
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
    /** A line of detail under the name — "1920×1080 · 2.4 MB". */
    meta?: string
    /** Shown on the picture for a video — its length. */
    badge?: string
    selectable?: boolean
    selected?: boolean
  }>(),
  { selectable: false, selected: false },
)
</script>

<template>
  <button
    type="button"
    class="group block w-full min-w-0 rounded-xl text-left focus-visible:outline-2 focus-visible:outline-offset-4
           focus-visible:outline-brand-bright"
    :title="filename"
    :role="selectable ? 'checkbox' : undefined"
    :aria-checked="selectable ? selected : undefined"
    :aria-label="filename"
  >
    <span class="relative block overflow-hidden rounded-xl bg-raised">
      <!-- Height from a width-relative spacer, not aspect-ratio: see MediaPicker.vue. -->
      <span class="block pt-[75%]" aria-hidden="true" />
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        :alt="filename"
        class="absolute inset-0 size-full object-cover transition-transform duration-300
               ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="!selectable && 'group-hover:scale-[1.03]'"
        loading="lazy"
      />
      <span
        v-if="kind === 'video'"
        class="absolute bottom-2 left-2 inline-flex items-center gap-0.5 rounded-full bg-ink/70 py-0.5 pr-2 pl-1
               text-[11px] text-ink-inverse"
        aria-hidden="true"
      >
        <IconPlayArrow class="size-3.5" />
        {{ badge ?? 'Video' }}
      </span>

      <template v-if="selectable">
        <span
          v-if="selected"
          class="absolute inset-0 rounded-xl bg-brand/25 ring-3 ring-brand ring-inset"
          aria-hidden="true"
        />
        <span
          class="absolute top-2 right-2 flex size-6 items-center justify-center rounded-full border-2
                 transition-colors duration-150"
          :class="selected ? 'border-brand bg-brand text-ink-inverse' : 'border-white bg-ink/25 text-transparent'"
          aria-hidden="true"
        >
          <IconCheck class="size-4" />
        </span>
      </template>
    </span>
    <span class="mt-2 block truncate px-0.5 text-[13px] text-ink">{{ filename }}</span>
    <span v-if="meta" class="block truncate px-0.5 text-[12px] text-ink-muted">{{ meta }}</span>
  </button>
</template>
