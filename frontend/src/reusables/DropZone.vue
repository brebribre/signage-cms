<script setup lang="ts">
import { ref } from 'vue'

/** Generic: takes files and emits them. It must not know what media is. */
const props = defineProps<{ accept?: string; label?: string; hint?: string }>()
const emit = defineEmits<{ files: [File[]] }>()

const isOver = ref(false)
const input = ref<HTMLInputElement | null>(null)

function onDrop(e: DragEvent) {
  isOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (files.length) emit('files', files)
}

function onPick(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  if (files.length) emit('files', files)
  // Reset, so picking the same file twice in a row still fires a change event.
  target.value = ''
}
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10
           text-center transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="isOver ? 'border-ink bg-raised' : 'border-line-strong bg-surface'"
    @dragover.prevent="isOver = true"
    @dragleave.prevent="isOver = false"
    @drop.prevent="onDrop"
  >
    <p class="text-sm text-ink">{{ label ?? 'Drop files here' }}</p>
    <p v-if="hint" class="mt-1 text-[13px] text-ink-subtle">{{ hint }}</p>
    <button
      type="button"
      class="mt-3 rounded-full border-2 border-ink px-4 py-1.5 text-[13px] text-ink
             transition-colors duration-200 hover:bg-raised"
      @click="input?.click()"
    >
      Choose files
    </button>
    <input
      ref="input"
      type="file"
      multiple
      class="hidden"
      :accept="props.accept"
      @change="onPick"
    />
  </div>
</template>
