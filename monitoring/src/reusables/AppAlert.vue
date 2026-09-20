<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'neutral' | 'danger' }>(), { tone: 'neutral' })
</script>

<template>
  <div
    class="rounded-lg px-3 py-2 text-[13px]"
    :class="tone === 'danger' ? 'bg-raised text-danger' : 'bg-raised text-ink-muted'"
    role="alert"
  >
    <slot />
  </div>
</template>
