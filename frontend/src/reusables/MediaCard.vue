<script setup lang="ts">
/** Presentational only — it is handed strings and a URL, and knows nothing about accounts
 *  or uploads. */
defineProps<{
  filename: string
  kind: 'image' | 'video'
  thumbnailUrl: string | null
  meta: string
}>()
</script>

<template>
  <div
    class="group flex cursor-pointer flex-col overflow-hidden rounded-xl bg-surface
           transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] hover:bg-raised"
  >
    <div class="relative aspect-video w-full overflow-hidden bg-raised">
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        :alt="filename"
        class="size-full object-cover"
        loading="lazy"
      />
      <div v-else class="flex size-full items-center justify-center text-[13px] text-ink-subtle">
        No preview
      </div>
      <span
        v-if="kind === 'video'"
        class="absolute bottom-1.5 left-1.5 rounded-sm bg-ink/80 px-1.5 py-0.5 text-[11px]
               uppercase tracking-wide text-ink-inverse"
      >
        Video
      </span>
    </div>
    <div class="min-w-0 p-3">
      <p class="truncate text-sm text-ink">{{ filename }}</p>
      <p class="mt-0.5 truncate text-[13px] text-ink-muted">{{ meta }}</p>
    </div>
  </div>
</template>
