<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{ title?: string; size?: 'md' | 'xl' }>(), {
  size: 'md',
})
const emit = defineEmits<{ close: [] }>()

const WIDTH = { md: 'max-w-md', xl: 'max-w-4xl' } as const

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
    <div class="w-full rounded-xl bg-canvas p-5" :class="WIDTH[props.size]">
      <h2 v-if="title" class="text-lg">{{ title }}</h2>
      <div class="mt-3"><slot /></div>
    </div>
  </div>
</template>
