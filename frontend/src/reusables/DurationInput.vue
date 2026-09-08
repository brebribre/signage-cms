<script setup lang="ts">
const model = defineModel<number>({ default: 10 })
defineProps<{ min?: number; max?: number }>()
</script>

<template>
  <div class="inline-flex items-center gap-1">
    <input
      v-model.number="model"
      type="number"
      :min="min ?? 1"
      :max="max ?? 3600"
      class="w-16 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
             focus:border-ink focus:outline-none"
    />
    <span class="text-[13px] text-ink-subtle">s</span>
  </div>
</template>
