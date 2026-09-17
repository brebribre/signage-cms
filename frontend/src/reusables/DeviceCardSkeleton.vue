<script setup lang="ts">
/** The shape of a DeviceCard while screens load: the screen drawing, a name, three facts. */
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
</script>

<template>
  <div class="rounded-2xl bg-canvas p-4" aria-hidden="true">
    <div class="flex items-center gap-4 sm:gap-6">
      <div class="flex size-[88px] shrink-0 items-center justify-center">
        <SkeletonBlock class="h-[50px] w-[88px] rounded-sm" />
      </div>
      <div class="min-w-0 flex-1">
        <SkeletonBlock class="h-4 w-40 max-w-full rounded-md" />
        <div class="mt-3 flex flex-col gap-2.5 sm:max-w-md">
          <SkeletonBlock class="h-3 w-3/4 rounded-md" />
          <SkeletonBlock class="h-3 w-1/2 rounded-md" />
          <SkeletonBlock class="h-3 w-1/3 rounded-md" />
        </div>
      </div>
    </div>
  </div>
</template>
