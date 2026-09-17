<script setup lang="ts">
/** The shape of a Playlists or Campaigns row while it loads: a title, a line of detail, and —
 *  for playlists — the row of thumbnails on the right. */
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'

withDefaults(defineProps<{ thumbnails?: number }>(), { thumbnails: 0 })
</script>

<template>
  <div class="rounded-2xl bg-canvas p-4" aria-hidden="true">
    <div class="flex items-center gap-4">
      <div class="min-w-0 flex-1">
        <SkeletonBlock class="h-4 w-48 max-w-full rounded-md" />
        <SkeletonBlock class="mt-2 h-3 w-64 max-w-full rounded-md" />
      </div>
      <div v-if="thumbnails" class="hidden shrink-0 gap-1.5 sm:flex">
        <SkeletonBlock v-for="i in thumbnails" :key="i" class="size-14 rounded-lg" />
      </div>
    </div>
  </div>
</template>
