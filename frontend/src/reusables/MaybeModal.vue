<script setup lang="ts">
/** Its content as a dialog, or simply inline — for UI that is part of the page in one mode and a
 *  dialog in another, without writing it twice. The campaign screen picker and schedule editor
 *  are a step of their own when creating, and a dialog opened from a summary card when editing. */
import AppModal from '@/reusables/AppModal.vue'

withDefaults(defineProps<{ asModal: boolean; title?: string; size?: 'md' | 'xl' }>(), { size: 'md' })
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <AppModal v-if="asModal" :title="title" :size="size" @close="emit('close')">
    <!-- A tall editor must scroll inside the dialog, not push its buttons off-screen. -->
    <div class="-mr-2 max-h-[72vh] overflow-y-auto pr-2">
      <slot />
    </div>
  </AppModal>
  <slot v-else />
</template>
