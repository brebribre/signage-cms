<script setup lang="ts">
/**
 * Every variant is the same pill silhouette carrying a 1px border, as on fortu.co.id.
 * That is what lets a solid and an outline button sit side by side without one appearing
 * to shift — the border is present in both, only its colour changes.
 *
 * Primary is the brand blue; secondary and ghost stay ink, so one blue button leads per view.
 *
 * Motion: every button rises 2px under the pointer and presses in on click — quick enough to feel
 * like a response rather than an effect, and off entirely for anyone who has asked their system
 * for reduced motion. The button is a `group`, so an icon inside can join in (the + on create
 * buttons turns a quarter).
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
  primary: 'border-brand bg-brand text-ink-inverse hover:bg-brand-strong hover:border-brand-strong',
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
    class="group inline-flex items-center justify-center gap-2 rounded-full border font-normal
           transition-[color,background-color,border-color,transform] duration-200
           ease-[cubic-bezier(0.4,0,0.2,1)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.97]
           active:duration-75 motion-reduce:transform-none motion-reduce:transition-colors
           focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright
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
