<script setup lang="ts">
/**
 * The hero's picture: the Publish scene, one signage totem beside the CMS window, publishing to
 * it on a sweep of the blues, the same picture at every width.
 *
 * On a phone it runs edge to edge, the totem sitting where the page's margin would be. From
 * tablet width up it keeps to the page's column, the totem flush with the headline's left edge,
 * and the CMS window runs on off the page's right edge.
 */
import PublishScene from './PublishScene.vue'
</script>

<template>
  <div class="@container relative -mx-5 sm:mx-0">
    <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[6%] h-[86%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
    <PublishScene hero class="relative sm:max-w-xl lg:max-w-[46rem]" />
  </div>
</template>
