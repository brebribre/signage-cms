<script setup lang="ts">
/** A big "you haven't done this yet" prompt: one icon, one line of why, one button. Shown in
 *  place of a missing first step (no screens, no media, no playlists) rather than an empty list
 *  that leaves someone guessing what to do next. */
import type { Component } from 'vue'

import AppButton from '@/reusables/AppButton.vue'

defineProps<{ icon: Component; title: string; description: string; action: string }>()
const emit = defineEmits<{ action: [] }>()
</script>

<template>
  <div class="flex flex-col items-start gap-5 rounded-xl bg-surface p-6 sm:flex-row sm:items-center sm:p-8">
    <span class="flex size-14 shrink-0 items-center justify-center rounded-full bg-ink text-ink-inverse">
      <component :is="icon" class="size-7" />
    </span>
    <div class="min-w-0 flex-1">
      <h2 class="text-xl">{{ title }}</h2>
      <p class="mt-1 text-sm text-ink-muted">{{ description }}</p>
    </div>
    <AppButton class="shrink-0" @click="emit('action')">{{ action }}</AppButton>
  </div>
</template>
