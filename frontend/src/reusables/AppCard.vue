<script setup lang="ts">
/**
 * A white card on the page's tint, with a hairline to hold its shape where it happens to sit on
 * white (inside a dialog). No shadows anywhere in this system, so depth is the tint and nothing
 * else. An interactive card deepens on hover.
 */
withDefaults(defineProps<{ interactive?: boolean; padded?: boolean }>(), {
  interactive: false,
  padded: true,
})
</script>

<template>
  <div
    class="rounded-2xl border border-line bg-canvas transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="[padded && 'p-4', interactive && 'cursor-pointer hover:bg-surface']"
  >
    <slot />
  </div>
</template>
