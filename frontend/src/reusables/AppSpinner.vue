<script setup lang="ts">
/** A circular "working" indicator, in the current text colour. The same ring AppButton draws
 *  while loading, for the places that aren't a button — a status line that's still moving. */
withDefaults(defineProps<{ size?: 'sm' | 'md' | 'lg'; label?: string }>(), { size: 'md', label: 'Working' })

const SIZE = { sm: 'size-3.5 border-2', md: 'size-5 border-2', lg: 'size-7 border-[3px]' } as const
</script>

<template>
  <span
    class="inline-block shrink-0 animate-spin rounded-full border-current border-t-transparent motion-reduce:animate-none motion-reduce:border-dashed"
    :class="SIZE[size]"
    role="status"
    :aria-label="label"
  />
</template>
