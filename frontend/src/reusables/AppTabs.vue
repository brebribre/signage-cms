<script setup lang="ts">
/**
 * Text tabs with a sliding underline instead of the pill style used for multi-select
 * toggles elsewhere (day pickers, kiosk levels) — a tab bar is single-choice navigation, not
 * a set of options, and looking different from those pills makes that distinction visible at
 * a glance.
 *
 * The underline's position is measured (JS, not CSS), because label widths vary — spans of
 * `translateX`/`width` are set from each button's own `offsetLeft`/`offsetWidth` rather than
 * guessed. The transition is suppressed for exactly one frame on mount so the bar appears
 * under the initial tab instead of sliding in from the left edge.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  items: readonly { value: string; label: string; badge?: number }[]
  modelValue: string
}>()
defineEmits<{ 'update:modelValue': [string] }>()

const tabEls = new Map<string, HTMLButtonElement>()
function setTabRef(value: string, el: Element | null) {
  if (el) tabEls.set(value, el as HTMLButtonElement)
  else tabEls.delete(value)
}

const bar = ref({ left: 0, width: 0 })
const settled = ref(false)

function measure() {
  const el = tabEls.get(props.modelValue)
  if (!el) return
  bar.value = { left: el.offsetLeft, width: el.offsetWidth }
}

onMounted(async () => {
  await nextTick()
  measure()
  requestAnimationFrame(() => { settled.value = true })
  window.addEventListener('resize', measure)
})
onBeforeUnmount(() => window.removeEventListener('resize', measure))
watch(() => props.modelValue, () => nextTick(measure))
</script>

<template>
  <div class="relative flex items-center gap-5 border-b border-line">
    <button
      v-for="item in items"
      :key="item.value"
      :ref="(el) => setTabRef(item.value, el as Element | null)"
      type="button"
      class="py-2.5 text-sm transition-colors duration-200"
      :class="modelValue === item.value ? 'text-ink' : 'text-ink-muted hover:text-ink'"
      @click="$emit('update:modelValue', item.value)"
    >
      {{ item.label }}
      <span v-if="item.badge" class="text-ink-subtle">&nbsp;{{ item.badge }}</span>
    </button>
    <span
      class="absolute bottom-0 h-0.5 rounded-full bg-ink"
      :style="{
        transform: `translateX(${bar.left}px)`,
        width: `${bar.width}px`,
        transition: settled ? 'transform 260ms cubic-bezier(0.4,0,0.2,1), width 260ms cubic-bezier(0.4,0,0.2,1)' : 'none',
      }"
    />
  </div>
</template>
