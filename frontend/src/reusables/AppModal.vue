<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

defineProps<{ title?: string }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
    @click.self="emit('close')"
  >
    <!-- The panel is a card, so it carries no border either — only the scrim separates it. -->
    <div class="w-full max-w-md rounded-xl bg-canvas p-5">
      <h2 v-if="title" class="text-lg">{{ title }}</h2>
      <div class="mt-3"><slot /></div>
    </div>
  </div>
</template>
