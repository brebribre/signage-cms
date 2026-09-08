<script setup lang="ts">
/**
 * The FORTU wordmark: tracked out and slightly stretched, as on fortu.co.id. No system
 * font ships an extended width, so the stretch is a transform — and it grows from the
 * transform origin, which is why `align` exists: a left-anchored logo drifts right of
 * centre when its parent centres it.
 */
withDefaults(defineProps<{ size?: 'sm' | 'md'; align?: 'left' | 'center' }>(), {
  size: 'md',
  align: 'left',
})
</script>

<template>
  <span
    class="inline-block font-medium uppercase text-ink"
    :class="[
      size === 'sm' ? 'text-sm tracking-[0.18em]' : 'text-base tracking-[0.2em]',
      align === 'center' ? 'origin-center' : 'origin-left',
    ]"
    style="transform: scaleX(1.08)"
    >Fortu<span class="text-ink-muted">&nbsp;CMS</span></span
  >
</template>
