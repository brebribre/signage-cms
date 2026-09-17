<script setup lang="ts">
/** A thin progress bar. `indeterminate` is for a step with no measurable progress (preparing a
 *  file, the server confirming it): a sliding segment, so the bar visibly keeps working instead of
 *  sitting still and looking frozen. Still for anyone who asked for reduced motion. */
withDefaults(defineProps<{ value?: number; indeterminate?: boolean }>(), { value: 0, indeterminate: false })
</script>

<template>
  <div class="relative h-1 w-full overflow-hidden rounded-full bg-raised" role="progressbar"
       :aria-valuenow="indeterminate ? undefined : Math.round(Math.min(1, Math.max(0, value)) * 100)"
       aria-valuemin="0" aria-valuemax="100">
    <div
      v-if="indeterminate"
      class="progress-indeterminate absolute inset-y-0 w-1/3 rounded-full bg-brand"
    />
    <div
      v-else
      class="h-full rounded-full bg-brand transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
      :style="{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }"
    />
  </div>
</template>

<style scoped>
.progress-indeterminate {
  animation: progress-slide 1.1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes progress-slide {
  from { left: -33%; }
  to { left: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .progress-indeterminate {
    animation: none;
    left: 0;
    width: 100%;
    opacity: 0.4;
  }
}
</style>
