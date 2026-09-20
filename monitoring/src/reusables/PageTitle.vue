<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <!-- Wraps: when the title is too long to share a line with the actions, the actions drop
       below it, instead of squeezing it into a narrow column. -->
  <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
    <div class="min-w-0 flex-auto">
      <!-- One size on every page — pages differ in what sits beside the title, never in how big
           it is. Smaller on phones, where a large title ate the first screenful. Tracking comes
           from the h1 rule in style.css. Long names wrap rather than truncate: a title is
           the one place the whole name must be readable. -->
      <h1 class="text-2xl [overflow-wrap:anywhere] sm:text-4xl"><slot name="title">{{ title }}</slot></h1>
      <p v-if="subtitle" class="mt-1 text-sm text-ink-muted">{{ subtitle }}</p>
    </div>
    <div class="shrink-0"><slot name="actions" /></div>
  </div>
</template>
