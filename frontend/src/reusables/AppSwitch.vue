<script setup lang="ts">
/**
 * A real on/off switch — track + sliding thumb — for a boolean that takes effect immediately
 * on click, as opposed to AppButton's pill toggles (which read as "choose one of these
 * options," better suited to something like day-of-week pickers). Same monochrome language
 * as everywhere else: filled ink when on, an outline when off, no accent hue.
 */
withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="model"
    :disabled="disabled"
    class="relative h-7 w-12 shrink-0 rounded-full border transition-colors duration-200
           focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink
           disabled:opacity-40 disabled:pointer-events-none"
    :class="model ? 'border-ink bg-ink' : 'border-line-strong bg-canvas'"
    @click="model = !model"
  >
    <span
      class="absolute top-[3px] left-[3px] size-5 rounded-full transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
      :class="model ? 'translate-x-5 bg-canvas' : 'translate-x-0 bg-ink'"
    />
  </button>
</template>
