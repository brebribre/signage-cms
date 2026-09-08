<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center rounded-xl bg-surface px-6 py-16 text-center">
    <h3 class="text-lg text-ink">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-sm text-sm text-ink-muted">{{ description }}</p>
    <div class="mt-4"><slot name="actions" /></div>
  </div>
</template>
