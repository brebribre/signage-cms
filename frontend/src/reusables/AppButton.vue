<script setup lang="ts">
/**
 * Every variant is the same pill silhouette carrying a 2px border, as on fortu.co.id.
 * That is what lets a solid and an outline button sit side by side without one appearing
 * to shift — the border is present in both, only its colour changes.
 *
 * There is no accent hue in this system, so emphasis is ink fill and nothing else.
 */
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md'
    type?: 'button' | 'submit'
    disabled?: boolean
    loading?: boolean
    block?: boolean
  }>(),
  { variant: 'primary', size: 'md', type: 'button', disabled: false, loading: false, block: false },
)

const VARIANTS = {
  primary: 'border-ink bg-ink text-ink-inverse hover:bg-ink-muted hover:border-ink-muted',
  secondary: 'border-ink bg-transparent text-ink hover:bg-raised',
  ghost: 'border-transparent bg-transparent text-ink-muted hover:text-ink hover:bg-raised',
  danger: 'border-danger bg-transparent text-danger hover:bg-danger hover:text-ink-inverse',
} as const

const SIZES = {
  sm: 'px-3 py-1 text-[13px]',
  md: 'px-4 py-2 text-sm',
} as const
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="inline-flex items-center justify-center gap-2 rounded-full border-2 font-normal
           transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
           focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink
           disabled:opacity-40 disabled:pointer-events-none"
    :class="[VARIANTS[variant], SIZES[size], block && 'w-full']"
  >
    <span
      v-if="loading"
      class="size-3.5 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
    <slot />
  </button>
</template>
