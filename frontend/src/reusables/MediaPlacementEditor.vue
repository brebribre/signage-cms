<script setup lang="ts">
import { computed, ref } from 'vue'

import { cropRectToStyle, resolveCropRect } from '@/utils/cropMath'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import type { ItemFit } from '@/types/api'
import AppButton from '@/reusables/AppButton.vue'

const props = defineProps<{
  row: DraftItem
  referenceScreen: { width: number; height: number; label: string }
}>()

const emit = defineEmits<{
  apply: [patch: Partial<DraftItem>]
  close: []
}>()

const FITS: { value: ItemFit; label: string }[] = [
  { value: 'contain', label: 'Contain' },
  { value: 'cover', label: 'Fill' },
  { value: 'stretch', label: 'Stretch' },
]

// A local working copy — nothing here reaches the draft row until Apply.
const fit = ref<ItemFit>(props.row.fit)
const cropX = ref(props.row.cropX ?? 0.5)
const cropY = ref(props.row.cropY ?? 0.5)
const cropZoom = ref(props.row.cropZoom ?? 1)
const hasAudio = ref(props.row.hasAudio)

const hasDimensions = computed(() => !!props.row.mediaWidth && !!props.row.mediaHeight)
const targetAspect = computed(() => props.referenceScreen.width / props.referenceScreen.height)

// --- Frame: sized to the reference screen's real aspect ratio, same technique as
// ScreenPreview.vue — width derived from a height cap, so the ratio is exact in both
// orientations instead of silently rendering at the *container's* aspect ratio. Contain and
// Stretch preview inside this exact frame too, not just Fill, so every mode shows the truth
// about the real device shape.

const FRAME_MAX_HEIGHT = 420
const frameWidthPx = computed(() => Math.round(FRAME_MAX_HEIGHT * targetAspect.value))
const frameOuterStyle = computed(() => ({ width: `min(100%, ${frameWidthPx.value}px)` }))
const frameStyle = computed(() => ({
  aspectRatio: `${props.referenceScreen.width} / ${props.referenceScreen.height}`,
}))

const OBJECT_FIT = { contain: 'contain', stretch: 'fill' } as const

// --- Crop (Fill only): hand-rolled pan (drag) + zoom (slider), on the raw <img>/<video>
// itself — the same technique every "move and scale" step (Instagram, Google Photos, Canva)
// actually uses: an absolutely positioned media element inside an overflow-hidden box, sized
// and offset from the current (center, zoom) via resolveCropRect, dragged by tracking pointer
// delta against the box's own rendered size.

const boxRef = ref<HTMLElement | null>(null)
const dragging = ref(false)
let dragStartPointer = { x: 0, y: 0 }
let dragStartCrop = { x: 0.5, y: 0.5 }

const cropRect = computed(() =>
  hasDimensions.value
    ? resolveCropRect(
        props.row.mediaWidth!, props.row.mediaHeight!, targetAspect.value,
        cropX.value, cropY.value, cropZoom.value,
      )
    : null,
)
const cropStyle = computed(() => (cropRect.value ? cropRectToStyle(cropRect.value) : {}))

function releaseCapture(e: PointerEvent) {
  const el = e.currentTarget as HTMLElement
  // Without this, a drag that ends outside the element (or a synthetic pointerup a browser
  // doesn't auto-release for) leaves this element capturing the pointer — every subsequent
  // click anywhere on the page silently gets routed here instead, including Apply/Cancel.
  if (el.hasPointerCapture?.(e.pointerId)) el.releasePointerCapture(e.pointerId)
}

function onPointerDown(e: PointerEvent) {
  if (!hasDimensions.value) return
  dragging.value = true
  dragStartPointer = { x: e.clientX, y: e.clientY }
  dragStartCrop = { x: cropX.value, y: cropY.value }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value || !boxRef.value) return
  const box = boxRef.value.getBoundingClientRect()
  // Dragging the visible window right means panning the underlying media left, hence the
  // minus sign — matches how every "drag the photo" cropper feels.
  //
  // Clamped to [0,1] here, not just at resolve time: resolveCropRect's own clamp is tighter
  // and aspect/zoom-dependent (right for rendering, since it varies per target device), but
  // the *stored* value needs a fixed, zoom-independent bound that matches what the backend
  // actually validates (crop_x/crop_y are `ge=0, le=1`) — an unclamped drag that runs the
  // photo off past the edge would otherwise save fine locally and then 422 on Save.
  cropX.value = Math.min(1, Math.max(0, dragStartCrop.x - (e.clientX - dragStartPointer.x) / box.width))
  cropY.value = Math.min(1, Math.max(0, dragStartCrop.y - (e.clientY - dragStartPointer.y) / box.height))
}

function onPointerUp(e: PointerEvent) {
  dragging.value = false
  releaseCapture(e)
}

function apply() {
  emit('apply', {
    fit: fit.value,
    cropX: cropX.value,
    cropY: cropY.value,
    cropZoom: cropZoom.value,
    hasAudio: props.row.kind === 'video' ? hasAudio.value : false,
  })
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between gap-3">
      <div class="min-w-0">
        <p class="truncate text-sm text-ink">{{ row.filename }}</p>
        <p class="text-[13px] text-ink-subtle">Editing for {{ referenceScreen.label }}</p>
      </div>
      <div class="flex shrink-0 gap-1 rounded-md bg-raised p-0.5">
        <button
          v-for="f in FITS"
          :key="f.value"
          type="button"
          class="rounded px-2.5 py-1 text-[13px] transition-colors duration-150"
          :class="fit === f.value ? 'bg-canvas text-ink shadow-sm' : 'text-ink-muted'"
          @click="fit = f.value"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <div v-if="!hasDimensions" class="rounded-xl bg-surface p-4 text-[13px] text-danger">
      This file's dimensions aren't known yet, so it can't be previewed here.
    </div>

    <template v-else>
      <div class="flex flex-col items-center gap-2">
        <div class="relative overflow-hidden rounded-xl bg-black" :style="frameOuterStyle">
          <div class="relative" :style="frameStyle">
            <!-- Fill: draggable pan + zoom. Contain/Stretch: plain object-fit, no interaction —
                 there is nothing to place, the whole point is showing the automatic result. -->
            <div
              v-if="fit === 'cover'"
              ref="boxRef"
              class="absolute inset-0 cursor-grab overflow-hidden active:cursor-grabbing"
              @pointerdown="onPointerDown"
              @pointermove="onPointerMove"
              @pointerup="onPointerUp"
              @pointercancel="onPointerUp"
            >
              <img
                v-if="row.kind === 'image'"
                :src="row.url"
                :alt="row.filename"
                class="absolute max-w-none select-none"
                :style="cropStyle"
                draggable="false"
              />
              <video
                v-else
                :src="row.url"
                class="absolute select-none"
                :style="cropStyle"
                :muted="!hasAudio"
                loop
                playsinline
                autoplay
                draggable="false"
              />
            </div>
            <template v-else>
              <img
                v-if="row.kind === 'image'"
                :src="row.url"
                :alt="row.filename"
                class="absolute inset-0 size-full"
                :style="{ objectFit: OBJECT_FIT[fit] }"
              />
              <video
                v-else
                :src="row.url"
                class="absolute inset-0 size-full"
                :style="{ objectFit: OBJECT_FIT[fit] }"
                :muted="!hasAudio"
                loop
                playsinline
                autoplay
              />
            </template>
          </div>
        </div>

        <div v-if="fit === 'cover'" class="flex items-center gap-2" :style="frameOuterStyle">
          <span class="text-[13px] text-ink-subtle">Zoom</span>
          <input
            v-model.number="cropZoom" type="range" min="1" max="3" step="0.01"
            class="flex-1 accent-ink"
          />
        </div>
        <p v-else class="text-center text-[13px] text-ink-muted" :style="frameOuterStyle">
          <span v-if="fit === 'contain'">The whole file shows, letterboxed — nothing to place.</span>
          <span v-else>Stretched to fill exactly, which may distort it — nothing to place.</span>
        </p>
      </div>

      <label v-if="row.kind === 'video'" class="flex items-center gap-2 text-sm text-ink">
        <input v-model="hasAudio" type="checkbox" class="size-4 accent-ink" />
        Play with sound
        <span class="text-[13px] text-ink-subtle">(every video is muted by default)</span>
      </label>
    </template>

    <div class="flex justify-end gap-2">
      <AppButton variant="secondary" size="sm" @click="emit('close')">Cancel</AppButton>
      <AppButton size="sm" @click="apply">Apply</AppButton>
    </div>
  </div>
</template>
