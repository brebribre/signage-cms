<script setup lang="ts">
/**
 * A control needs a visible target before it is focused, so inputs keep a border even
 * though cards do not. Focus is a darker line rather than a colour, since there is none.
 */
defineProps<{
  label?: string
  id?: string
  type?: string
  placeholder?: string
  autocomplete?: string
  hint?: string
  error?: string | null
  required?: boolean
}>()

const model = defineModel<string>({ default: '' })
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label v-if="label" :for="id" class="text-[13px] text-ink-muted">
      {{ label }}
      <span v-if="required" class="text-ink-subtle">*</span>
    </label>
    <input
      :id="id"
      v-model="model"
      :type="type ?? 'text'"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      class="w-full rounded-lg border bg-canvas px-3 py-2 text-sm text-ink
             placeholder:text-ink-subtle transition-colors duration-150
             focus:border-ink focus:outline-none"
      :class="error ? 'border-danger' : 'border-line-strong'"
    />
    <p v-if="error" class="text-[13px] text-danger">{{ error }}</p>
    <p v-else-if="hint" class="text-[13px] text-ink-subtle">{{ hint }}</p>
  </div>
</template>
