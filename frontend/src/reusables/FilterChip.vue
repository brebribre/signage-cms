<script setup lang="ts">
defineProps<{ active: boolean; count?: number }>()
</script>

<template>
  <!-- Active state is ink fill, not a colour: the palette has no accent to use. -->
  <button
    type="button"
    class="rounded-full border-2 px-3 py-1 text-[13px] transition-colors duration-200
           ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="active
      ? 'border-ink bg-ink text-ink-inverse'
      : 'border-line-strong bg-transparent text-ink-muted hover:bg-raised hover:text-ink'"
  >
    <slot />
    <span v-if="count !== undefined" :class="active ? 'text-ink-inverse/60' : 'text-ink-subtle'">
      &nbsp;{{ count }}
    </span>
  </button>
</template>
