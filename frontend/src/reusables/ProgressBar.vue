<script setup lang="ts">
defineProps<{ value: number }>()
</script>

<template>
  <div class="h-1 w-full overflow-hidden rounded-full bg-raised">
    <div
      class="h-full rounded-full bg-ink transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
      :style="{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }"
    />
  </div>
</template>
