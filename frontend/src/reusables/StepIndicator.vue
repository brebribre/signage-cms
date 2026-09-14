<script setup lang="ts">
/** O────O────O. Completed steps are clickable, so going back never loses what was entered;
 *  steps ahead are not — each one depends on the one before it being valid. */
import IconCheck from '~icons/material-symbols/check'

defineProps<{ steps: string[]; current: number }>()
const emit = defineEmits<{ select: [index: number] }>()
</script>

<template>
  <ol class="flex items-center px-6 pb-7">
    <li
      v-for="(label, i) in steps"
      :key="label"
      class="flex items-center"
      :class="i < steps.length - 1 && 'flex-1'"
    >
      <button
        type="button"
        class="relative flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-[13px]
               transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
        :class="[
          i < current && 'cursor-pointer border-ink bg-ink text-ink-inverse hover:border-ink-muted hover:bg-ink-muted',
          i === current && 'cursor-default border-ink bg-canvas text-ink',
          i > current && 'cursor-default border-line-strong bg-canvas text-ink-subtle',
        ]"
        :disabled="i >= current"
        :aria-current="i === current ? 'step' : undefined"
        @click="emit('select', i)"
      >
        <IconCheck v-if="i < current" class="size-4" />
        <span v-else>{{ i + 1 }}</span>
        <span
          class="absolute top-full left-1/2 mt-2 -translate-x-1/2 whitespace-nowrap text-[13px]"
          :class="i <= current ? 'text-ink' : 'text-ink-subtle'"
        >
          {{ label }}
        </span>
      </button>
      <div
        v-if="i < steps.length - 1"
        class="mx-3 h-0.5 flex-1 rounded-full transition-colors duration-200"
        :class="i < current ? 'bg-ink' : 'bg-line'"
      />
    </li>
  </ol>
</template>
