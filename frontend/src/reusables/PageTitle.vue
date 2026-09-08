<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="flex items-start justify-between gap-4">
    <div class="min-w-0">
      <!-- One size everywhere. Pages differ in what sits beside the title, never in how
           big it is. Tracking comes from the h1 rule in style.css. -->
      <h1 class="truncate text-3xl sm:text-4xl">{{ title }}</h1>
      <p v-if="subtitle" class="mt-1 text-sm text-ink-muted">{{ subtitle }}</p>
    </div>
    <div class="shrink-0"><slot name="actions" /></div>
  </div>
</template>
