<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'

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
const trimStart = ref(props.row.trimStartSeconds)
const trimEnd = ref(props.row.trimEndSeconds)

const hasDimensions = computed(() => !!props.row.mediaWidth && !!props.row.mediaHeight)
const targetAspect = computed(() => props.referenceScreen.width / props.referenceScreen.height)

// --- Image crop, via vue-advanced-cropper ---

const cropperRef = ref<InstanceType<typeof Cropper> | null>(null)
let lastZoomInput = 1

function defaultSize() {
  if (!hasDimensions.value) return undefined
  const rect = resolveCropRect(
    props.row.mediaWidth!, props.row.mediaHeight!, targetAspect.value,
    cropX.value, cropY.value, cropZoom.value,
  )
  return { width: rect.w * props.row.mediaWidth!, height: rect.h * props.row.mediaHeight! }
}

function defaultPosition() {
  if (!hasDimensions.value) return undefined
  const rect = resolveCropRect(
    props.row.mediaWidth!, props.row.mediaHeight!, targetAspect.value,
    cropX.value, cropY.value, cropZoom.value,
  )
  return { left: rect.x * props.row.mediaWidth!, top: rect.y * props.row.mediaHeight! }
}

/** The cropper reports coordinates in source-image pixels — invert resolveCropRect's math to
 *  read them back as our normalized (center, zoom) model. */
function onCropperChange(result: { coordinates: { left: number; top: number; width: number; height: number } }) {
  if (!hasDimensions.value) return
  const mediaW = props.row.mediaWidth!
  const mediaH = props.row.mediaHeight!
  const { left, top, width, height } = result.coordinates
  cropX.value = (left + width / 2) / mediaW
  cropY.value = (top + height / 2) / mediaH
  // Baseline (zoom=1) width for this aspect, to read the cropper's own zoom back out.
  const baseline = resolveCropRect(mediaW, mediaH, targetAspect.value, 0.5, 0.5, 1)
  cropZoom.value = Math.max(1, baseline.w / (width / mediaW))
}

function onZoomSlider(e: Event) {
  const value = Number((e.target as HTMLInputElement).value)
  const factor = value / lastZoomInput
  lastZoomInput = value
  cropperRef.value?.zoom(factor)
}

// --- Video crop, hand-rolled pan (drag) + zoom (slider) on the <video> element itself ---

const videoBoxRef = ref<HTMLElement | null>(null)
const dragging = ref(false)
let dragStartPointer = { x: 0, y: 0 }
let dragStartCrop = { x: 0.5, y: 0.5 }

const videoRect = computed(() =>
  hasDimensions.value
    ? resolveCropRect(
        props.row.mediaWidth!, props.row.mediaHeight!, targetAspect.value,
        cropX.value, cropY.value, cropZoom.value,
      )
    : null,
)
const videoStyle = computed(() => (videoRect.value ? cropRectToStyle(videoRect.value) : {}))

function onVideoPointerDown(e: PointerEvent) {
  if (fit.value !== 'cover') return
  dragging.value = true
  dragStartPointer = { x: e.clientX, y: e.clientY }
  dragStartCrop = { x: cropX.value, y: cropY.value }
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}

function onVideoPointerMove(e: PointerEvent) {
  if (!dragging.value || !videoBoxRef.value) return
  const box = videoBoxRef.value.getBoundingClientRect()
  // Dragging the visible window right means panning the underlying media left, hence the
  // minus sign — matches how every "drag the photo" cropper (this Instagram one included) feels.
  cropX.value = dragStartCrop.x - (e.clientX - dragStartPointer.x) / box.width
  cropY.value = dragStartCrop.y - (e.clientY - dragStartPointer.y) / box.height
}

function onVideoPointerUp() {
  dragging.value = false
}

// --- Trim preview: scrub the same <video> to the handle being dragged ---

const previewVideoRef = ref<HTMLVideoElement | null>(null)
watch(trimStart, (v) => {
  if (previewVideoRef.value) previewVideoRef.value.currentTime = v
})
watch(trimEnd, (v) => {
  if (previewVideoRef.value && v != null) previewVideoRef.value.currentTime = v
})

const maxTrim = computed(() => props.row.mediaDuration ?? props.row.durationSeconds)

function apply() {
  emit('apply', {
    fit: fit.value,
    cropX: cropX.value,
    cropY: cropY.value,
    cropZoom: cropZoom.value,
    trimStartSeconds: props.row.kind === 'video' ? trimStart.value : 0,
    trimEndSeconds: props.row.kind === 'video' ? trimEnd.value : null,
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

    <div v-if="fit !== 'cover'" class="rounded-xl bg-surface p-4 text-[13px] text-ink-muted">
      <span v-if="fit === 'contain'">The whole file shows, letterboxed — nothing to crop.</span>
      <span v-else>Stretched to fill the screen exactly, which may distort it — nothing to crop.</span>
    </div>

    <div v-else-if="!hasDimensions" class="rounded-xl bg-surface p-4 text-[13px] text-danger">
      This file's dimensions aren't known yet, so it can't be cropped.
    </div>

    <template v-else>
      <!-- Image: vue-advanced-cropper does the drag/pinch/wheel-zoom work; stencil is locked to
           the device's aspect ratio and to move-only, so the only degree of freedom is pan/zoom,
           never an arbitrary crop shape. -->
      <div v-if="row.kind === 'image'" class="flex flex-col gap-2">
        <Cropper
          ref="cropperRef"
          class="h-80 rounded-xl bg-black"
          :src="row.url"
          :stencil-props="{ aspectRatio: targetAspect, movable: true, resizable: false }"
          :default-size="defaultSize"
          :default-position="defaultPosition"
          image-restriction="stencil"
          @change="onCropperChange"
        />
        <div class="flex items-center gap-2">
          <span class="text-[13px] text-ink-subtle">Zoom</span>
          <input
            type="range" min="1" max="3" step="0.01" :value="cropZoom"
            class="flex-1 accent-ink"
            @input="onZoomSlider"
          />
        </div>
      </div>

      <!-- Video: same visual language (bounded frame, dimmed outside), hand-rolled pan + zoom
           since no ready-made Vue video-cropper exists. -->
      <div v-else class="flex flex-col gap-3">
        <div
          ref="videoBoxRef"
          class="relative h-64 cursor-grab overflow-hidden rounded-xl bg-black active:cursor-grabbing"
          @pointerdown="onVideoPointerDown"
          @pointermove="onVideoPointerMove"
          @pointerup="onVideoPointerUp"
          @pointercancel="onVideoPointerUp"
        >
          <video
            ref="previewVideoRef"
            :src="row.url"
            class="absolute select-none"
            :style="videoStyle"
            muted
            loop
            playsinline
            autoplay
            draggable="false"
          />
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[13px] text-ink-subtle">Zoom</span>
          <input
            v-model.number="cropZoom" type="range" min="1" max="3" step="0.01"
            class="flex-1 accent-ink"
          />
        </div>

        <div class="flex flex-col gap-2 rounded-xl bg-surface p-3">
          <p class="text-[13px] text-ink-subtle">Trim</p>
          <div class="flex items-center gap-2">
            <input
              v-model.number="trimStart" type="number" min="0" :max="maxTrim" step="0.1"
              class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                     text-ink focus:border-ink focus:outline-none"
            />
            <span class="text-[13px] text-ink-subtle">to</span>
            <input
              :value="trimEnd ?? maxTrim"
              type="number" min="0" :max="maxTrim" step="0.1"
              class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                     text-ink focus:border-ink focus:outline-none"
              @input="trimEnd = Number(($event.target as HTMLInputElement).value)"
            />
            <span class="text-[13px] text-ink-subtle">of {{ maxTrim.toFixed(1) }}s</span>
          </div>
        </div>
      </div>
    </template>

    <div class="flex justify-end gap-2">
      <AppButton variant="secondary" size="sm" @click="emit('close')">Cancel</AppButton>
      <AppButton size="sm" @click="apply">Apply</AppButton>
    </div>
  </div>
</template>
