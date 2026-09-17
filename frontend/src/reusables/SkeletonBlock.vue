<script setup lang="ts">
/**
 * One placeholder shape while real content loads. Sized and rounded by the caller, so a skeleton
 * can match the shape of what will replace it — that is what makes the swap feel like content
 * arriving rather than the page rearranging.
 *
 * A soft sweep of light rather than a blink; still for anyone who has asked their system for
 * reduced motion. Always hidden from assistive tech — the list around it announces "Loading"
 * once (SkeletonList), instead of every block being read out.
 */
</script>

<template>
  <span class="skeleton-block relative block overflow-hidden bg-raised" aria-hidden="true" />
</template>

<style scoped>
.skeleton-block::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.6), transparent);
  animation: skeleton-sweep 1.4s ease-in-out infinite;
}
@keyframes skeleton-sweep {
  to {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-block::after {
    animation: none;
    display: none;
  }
}
</style>
