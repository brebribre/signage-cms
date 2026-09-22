<script setup lang="ts">
/**
 * The app's own dropdown, in place of the browser's native <select> — which draws its menu in
 * the operating system's style and can't be made to match the rest of the app.
 *
 * Built to the WAI-ARIA "select-only combobox" pattern, so it keeps what a native select gives
 * for free: Tab reaches it; Enter, Space or ↓/↑ open it; ↑/↓, Home and End move through the
 * options; typing jumps to the first option starting with those letters; Enter or Space picks;
 * Escape or Tab closes without changing anything. Clicking outside closes it too. The highlighted
 * option is announced through aria-activedescendant, so focus never leaves the button.
 */
import { computed, nextTick, onMounted, onUnmounted, ref, useId, watch } from 'vue'
import IconCheck from '~icons/material-symbols/check'
import IconExpandMore from '~icons/material-symbols/expand-more'

export interface SelectOption {
  value: string
  label: string
  /** Muted text after the label, e.g. "this browser". */
  hint?: string
}

const props = withDefaults(
  defineProps<{
    options: SelectOption[]
    /** Links to a visible <label for>, so the control is named by it. */
    id?: string
    placeholder?: string
    size?: 'sm' | 'md'
  }>(),
  { placeholder: 'Select…', size: 'md' },
)
const model = defineModel<string>({ required: true })

const uid = useId()
const buttonId = computed(() => props.id ?? `select-${uid}`)
const listId = `${uid}-list`
const optionId = (i: number) => `${uid}-opt-${i}`

const open = ref(false)
const active = ref(-1)
const root = ref<HTMLElement | null>(null)
const list = ref<HTMLElement | null>(null)

const selectedIndex = computed(() => props.options.findIndex((o) => o.value === model.value))
const selected = computed(() => props.options[selectedIndex.value] ?? null)

async function show(at = selectedIndex.value) {
  open.value = true
  active.value = at >= 0 ? at : 0
  await nextTick()
  scrollActiveIntoView()
}
function hide() {
  open.value = false
}
function choose(i: number) {
  const option = props.options[i]
  if (option) model.value = option.value
  hide()
}
function move(to: number) {
  active.value = Math.max(0, Math.min(props.options.length - 1, to))
  nextTick(scrollActiveIntoView)
}
function scrollActiveIntoView() {
  list.value?.querySelector<HTMLElement>(`#${CSS.escape(optionId(active.value))}`)?.scrollIntoView({ block: 'nearest' })
}

// Type-ahead: letters typed in quick succession build one search.
let typed = ''
let typedTimer: ReturnType<typeof setTimeout> | undefined
function typeAhead(key: string) {
  typed += key.toLowerCase()
  clearTimeout(typedTimer)
  typedTimer = setTimeout(() => { typed = '' }, 600)
  const from = open.value ? active.value : selectedIndex.value
  const order = [...props.options.keys()].map((k) => (k + Math.max(from, 0) + (typed.length === 1 ? 1 : 0)) % props.options.length)
  const hit = order.find((i) => props.options[i].label.toLowerCase().startsWith(typed))
  if (hit === undefined) return
  if (open.value) move(hit)
  else model.value = props.options[hit].value
}

function onKeydown(e: KeyboardEvent) {
  const last = props.options.length - 1
  if (!open.value) {
    if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
      e.preventDefault()
      show(e.key === 'ArrowUp' && selectedIndex.value < 0 ? last : selectedIndex.value)
    } else if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
      typeAhead(e.key)
    }
    return
  }
  switch (e.key) {
    case 'ArrowDown': e.preventDefault(); move(active.value + 1); break
    case 'ArrowUp': e.preventDefault(); move(active.value - 1); break
    case 'Home': e.preventDefault(); move(0); break
    case 'End': e.preventDefault(); move(last); break
    case 'Enter':
    case ' ': e.preventDefault(); choose(active.value); break
    case 'Escape': e.preventDefault(); hide(); break
    case 'Tab': hide(); break
    default:
      if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) typeAhead(e.key)
  }
}

function onDocPointer(e: PointerEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) hide()
}
onMounted(() => document.addEventListener('pointerdown', onDocPointer))
onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointer)
  clearTimeout(typedTimer)
})
watch(() => props.options, () => { if (active.value > props.options.length - 1) active.value = props.options.length - 1 })
</script>

<template>
  <div ref="root" class="relative">
    <button
      :id="buttonId"
      type="button"
      role="combobox"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="listId"
      :aria-activedescendant="open && active >= 0 ? optionId(active) : undefined"
      class="flex w-full items-center gap-2 rounded-lg border bg-canvas text-left text-ink transition-colors
             duration-150 hover:border-ink-muted focus-visible:border-brand focus-visible:outline-none"
      :class="[
        size === 'sm' ? 'py-1.5 pr-2 pl-3 text-[13px]' : 'py-2 pr-2.5 pl-3 text-sm',
        open ? 'border-brand' : 'border-line-strong',
      ]"
      @click="open ? hide() : show()"
      @keydown="onKeydown"
    >
      <span class="min-w-0 flex-1 truncate" :class="!selected && 'text-ink-subtle'">
        {{ selected?.label ?? placeholder }}
        <span v-if="selected?.hint" class="text-ink-subtle">· {{ selected.hint }}</span>
      </span>
      <IconExpandMore
        class="size-4 shrink-0 text-ink-muted transition-transform duration-200"
        :class="open && 'rotate-180'"
        aria-hidden="true"
      />
    </button>

    <ul
      v-show="open"
      :id="listId"
      ref="list"
      role="listbox"
      :aria-labelledby="buttonId"
      tabindex="-1"
      class="absolute left-0 z-30 mt-1 max-h-64 w-full min-w-48 overflow-y-auto rounded-xl border border-line
             bg-canvas p-1"
    >
      <li
        v-for="(option, i) in options"
        :id="optionId(i)"
        :key="option.value"
        role="option"
        :aria-selected="option.value === model"
        class="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-[13px]"
        :class="[
          i === active ? 'bg-surface' : '',
          option.value === model ? 'font-medium text-brand' : 'text-ink',
        ]"
        @pointerenter="active = i"
        @pointerdown.prevent
        @click="choose(i)"
      >
        <span class="min-w-0 flex-1 truncate">
          {{ option.label }}
          <span v-if="option.hint" class="font-normal text-ink-subtle">· {{ option.hint }}</span>
        </span>
        <IconCheck v-if="option.value === model" class="size-4 shrink-0" aria-hidden="true" />
      </li>
    </ul>
  </div>
</template>
