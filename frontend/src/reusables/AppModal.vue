<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{ title?: string; size?: 'md' | 'xl' }>(), {
  size: 'md',
})
const emit = defineEmits<{ close: [] }>()

// From sm up only — on a phone the dialog is a full-width sheet.
const WIDTH = { md: 'sm:max-w-md', xl: 'sm:max-w-4xl' } as const

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex animate-fade-in items-end justify-center bg-ink/40
           motion-reduce:animate-none sm:items-center sm:p-4"
    @click.self="emit('close')"
  >
    <!-- The panel is a card, so it carries no border either — only the scrim separates it. It
         never grows past the viewport: the title stays put and the body scrolls, with a
         ModalActions row pinned to the body's bottom so the buttons are always reachable.
         On a phone it's a sheet like the iOS keyboard: full width, rising from the bottom edge,
         rounded on top, padded clear of the home indicator. Centered from sm up. -->
    <div
      class="flex max-h-[calc(100dvh_-_2.5rem)] w-full animate-sheet-up flex-col overflow-hidden rounded-t-2xl
             bg-canvas motion-reduce:animate-none sm:max-h-full sm:animate-none sm:rounded-xl"
      :class="WIDTH[props.size]"
    >
      <h2 v-if="title" class="shrink-0 px-5 pt-5 text-lg">{{ title }}</h2>
      <div
        class="min-h-0 overflow-y-auto px-5 pb-[calc(1.25rem_+_env(safe-area-inset-bottom))] sm:pb-5"
        :class="title ? 'pt-3' : 'pt-5'"
      >
        <slot />
      </div>
    </div>
  </div>
</template>
