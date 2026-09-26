<script setup lang="ts">
/**
 * A panel that slides in from the right over a dimmed page — for the details of one row, read
 * beside the list it came from rather than instead of it. Full width on a phone.
 *
 * Closes on the scrim, the ×, or Escape. `dismissible` false holds it open while a dialog sits
 * on top of it, so Escape closes that dialog and not both at once.
 */
import { onMounted, onUnmounted } from 'vue'
import IconClose from '~icons/material-symbols/close'

const props = withDefaults(defineProps<{ label: string; dismissible?: boolean }>(), { dismissible: true })
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.dismissible) emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="fixed inset-0 z-40 flex justify-end">
    <div class="absolute inset-0 animate-fade-in bg-ink/30 motion-reduce:animate-none" aria-hidden="true" @click="emit('close')" />
    <aside
      class="drawer relative flex h-full w-full flex-col bg-canvas sm:max-w-md sm:rounded-l-2xl"
      role="dialog"
      aria-modal="true"
      :aria-label="label"
    >
      <button
        type="button"
        class="absolute top-4 right-4 z-10 rounded-lg p-1.5 text-ink-muted transition-colors duration-150 hover:bg-raised
               hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
        aria-label="Close"
        @click="emit('close')"
      >
        <IconClose class="size-5" aria-hidden="true" />
      </button>
      <div class="min-h-0 flex-1 overflow-y-auto pb-[env(safe-area-inset-bottom)]">
        <slot />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.drawer {
  animation: drawer-in 320ms cubic-bezier(0.32, 0.72, 0, 1);
}
@keyframes drawer-in {
  from {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .drawer {
    animation: none;
  }
}
</style>
