<script setup lang="ts">
/**
 * Every variant is the same silhouette carrying a 1px border, so a solid and an outline button
 * sit side by side without one appearing to shift — the border is present in both, only its
 * colour changes.
 *
 * The shape and the blue are the marketing site's: `rounded-lg`, not a pill, and the cobalt
 * --color-action rather than the darker --color-brand. A button is the one thing on a page you
 * are meant to press, and it should look the same in the app as it does on the page that sold
 * it. Secondary and ghost stay ink, so one cobalt button leads per view.
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
  // Hover settles onto the logo blue, a clear step down from the cobalt rather than a darker
  // shade of it, which at this lightness would be hard to tell apart at a glance.
  primary: 'border-action bg-action text-white hover:bg-action-hover hover:border-action-hover',
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
    class="inline-flex items-center justify-center gap-2 rounded-lg border font-normal
           transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
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
