<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  cropRectToStyle,
  effectiveDimensions,
  resolveCropRect,
  ROTATION_WRAPPER_STYLE,
  rotationStyle,
} from '@/utils/cropMath'
import { mediaToDraftElement } from '@/hooks/usePlaylistEditor'
import type { DraftElement, DraftItem } from '@/hooks/usePlaylistEditor'
import type { MediaRead } from '@/types/api'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'

const props = defineProps<{
  item: DraftItem
  referenceScreen: { width: number; height: number; label: string }
  library: MediaRead[]
}>()

const emit = defineEmits<{
  apply: [elements: DraftElement[]]
  close: []
}>()

// A local working copy — nothing here reaches the draft scene until Apply.
const elements = ref<DraftElement[]>(props.item.elements.map((e) => ({ ...e })))
const selectedKey = ref<string | null>(null)
const selected = computed(() => elements.value.find((e) => e.key === selectedKey.value) ?? null)

function select(key: string | null) {
  selectedKey.value = key
}

/** Selecting-and-dragging brings an element to front — the same behavior every Canva-like
 *  tool has, without needing a separate reorder UI. */
function bringToFront(key: string) {
  const idx = elements.value.findIndex((e) => e.key === key)
  if (idx === -1) return
  const [el] = elements.value.splice(idx, 1)
  elements.value.push(el)
  elements.value.forEach((e, i) => { e.zIndex = i })
}

// --- Canvas frame: same width-from-height-cap technique as ScreenPreview.vue, so the ratio
// is exact in both orientations. ---

const FRAME_MAX_HEIGHT = 480
const canvasAspect = computed(() => props.referenceScreen.width / props.referenceScreen.height)
const frameWidthPx = computed(() => Math.round(FRAME_MAX_HEIGHT * canvasAspect.value))
const frameOuterStyle = computed(() => ({ width: `min(100%, ${frameWidthPx.value}px)` }))
const frameStyle = computed(() => ({
  aspectRatio: `${props.referenceScreen.width} / ${props.referenceScreen.height}`,
}))

const canvasRef = ref<HTMLElement | null>(null)

function releaseCapture(e: PointerEvent) {
  const el = e.currentTarget as HTMLElement
  if (el.hasPointerCapture?.(e.pointerId)) el.releasePointerCapture(e.pointerId)
}

// --- Drag an element to move it. Same technique as the crop pan this session already
// proved: track pointer delta against the CANVAS's own rendered size (never the rotated
// media inside it), so the math is exactly the same at every rotation. ---

const dragging = ref(false)
let dragStartPointer = { x: 0, y: 0 }
let dragStartBox = { x: 0, y: 0 }

function onElementPointerDown(el: DraftElement, e: PointerEvent) {
  select(el.key)
  bringToFront(el.key)
  dragging.value = true
  dragStartPointer = { x: e.clientX, y: e.clientY }
  dragStartBox = { x: el.x, y: el.y }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onElementPointerMove(e: PointerEvent) {
  if (!dragging.value || !selected.value || !canvasRef.value) return
  const box = canvasRef.value.getBoundingClientRect()
  selected.value.x = dragStartBox.x + (e.clientX - dragStartPointer.x) / box.width
  selected.value.y = dragStartBox.y + (e.clientY - dragStartPointer.y) / box.height
}

function onElementPointerUp(e: PointerEvent) {
  dragging.value = false
  releaseCapture(e)
}

// --- Resize via corner handles — free (unlocked) aspect, matches "enlarge or make it
// smaller" as asked. Each corner keeps the OPPOSITE corner fixed as the anchor. ---

type Corner = 'nw' | 'ne' | 'sw' | 'se'
const CORNERS: Corner[] = ['nw', 'ne', 'sw', 'se']
const MIN_SIZE = 0.05

const resizingCorner = ref<Corner | null>(null)
let resizeStartPointer = { x: 0, y: 0 }
let resizeStartBox = { x: 0, y: 0, width: 0, height: 0 }

function onHandlePointerDown(corner: Corner, e: PointerEvent) {
  if (!selected.value) return
  resizingCorner.value = corner
  resizeStartPointer = { x: e.clientX, y: e.clientY }
  resizeStartBox = {
    x: selected.value.x, y: selected.value.y,
    width: selected.value.width, height: selected.value.height,
  }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onHandlePointerMove(e: PointerEvent) {
  if (!resizingCorner.value || !selected.value || !canvasRef.value) return
  const box = canvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - resizeStartPointer.x) / box.width
  const dy = (e.clientY - resizeStartPointer.y) / box.height
  let { x, y, width, height } = resizeStartBox
  const corner = resizingCorner.value
  if (corner === 'se') { width += dx; height += dy }
  else if (corner === 'nw') { x += dx; width -= dx; y += dy; height -= dy }
  else if (corner === 'ne') { width += dx; y += dy; height -= dy }
  else if (corner === 'sw') { x += dx; width -= dx; height += dy }
  selected.value.x = x
  selected.value.y = y
  selected.value.width = Math.max(MIN_SIZE, width)
  selected.value.height = Math.max(MIN_SIZE, height)
}

function onHandlePointerUp(e: PointerEvent) {
  resizingCorner.value = null
  releaseCapture(e)
}

const HANDLE_POS: Record<Corner, { left: string; top: string }> = {
  nw: { left: '0%', top: '0%' },
  ne: { left: '100%', top: '0%' },
  sw: { left: '0%', top: '100%' },
  se: { left: '100%', top: '100%' },
}
const HANDLE_CURSOR: Record<Corner, string> = {
  nw: 'nwse-resize', se: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize',
}

// --- Rendering: cover-fit + rotation only in v1 — no per-element Fit/pan/zoom UI. An
// element's own box (x/y/width/height, as a fraction of the canvas) sets the target aspect
// ratio; resizing the box *is* the crop. Any crop_x/crop_y/crop_zoom already on an element
// from before this editor existed is still honored (not reset to center), just not
// editable here. ---

function elementTargetAspect(el: DraftElement): number {
  return (el.width / el.height) * canvasAspect.value
}

function cropWrapperStyle(el: DraftElement) {
  if (!el.mediaWidth || !el.mediaHeight) return {}
  const eff = effectiveDimensions(el.mediaWidth, el.mediaHeight, el.rotationDegrees)
  const rect = resolveCropRect(
    eff.width, eff.height, elementTargetAspect(el),
    el.cropX ?? 0.5, el.cropY ?? 0.5, el.cropZoom ?? 1,
  )
  return { position: 'absolute' as const, ...cropRectToStyle(rect), ...ROTATION_WRAPPER_STYLE }
}

function mediaStyle(el: DraftElement) {
  return rotationStyle(el.rotationDegrees)
}

// --- Per-element toolbar: rotate (90° cycle, video only), sound (video only), delete. ---

function rotateSelected() {
  if (!selected.value || selected.value.kind !== 'video') return
  selected.value.rotationDegrees = ((selected.value.rotationDegrees + 90) % 360)
}

function deleteSelected() {
  if (!selectedKey.value) return
  elements.value = elements.value.filter((e) => e.key !== selectedKey.value)
  selectedKey.value = null
}

// --- Add element: reuses the same multi-select-then-confirm picker pattern as "Add media"
// on the playlist row list, but appends into THIS scene's elements instead of new slots. ---

const picking = ref(false)
const picked = ref<Set<string>>(new Set())

function togglePick(mediaId: string) {
  const next = new Set(picked.value)
  next.has(mediaId) ? next.delete(mediaId) : next.add(mediaId)
  picked.value = next
}

function confirmPick() {
  const chosen = props.library.filter((m) => picked.value.has(m.id))
  let maxZ = Math.max(0, ...elements.value.map((e) => e.zIndex))
  let stagger = 0
  for (const m of chosen) {
    maxZ += 1
    elements.value.push(mediaToDraftElement(m, {
      x: 0.3 + stagger, y: 0.3 + stagger, width: 0.4, height: 0.4, zIndex: maxZ,
    }))
    stagger += 0.03
  }
  picked.value = new Set()
  picking.value = false
}

function apply() {
  emit('apply', elements.value)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between gap-3">
      <div class="min-w-0">
        <p class="text-sm text-ink">Scene</p>
        <p class="text-[13px] text-ink-subtle">Editing for {{ referenceScreen.label }}</p>
      </div>
      <AppButton variant="secondary" size="sm" @click="picking = true">Add element</AppButton>
    </div>

    <div class="flex justify-center" :style="frameOuterStyle">
      <div
        ref="canvasRef"
        class="relative w-full overflow-hidden rounded-xl bg-black"
        :style="frameStyle"
        @click.self="select(null)"
      >
        <div
          v-for="el in elements"
          :key="el.key"
          class="absolute cursor-grab touch-none select-none active:cursor-grabbing"
          :style="{
            left: `${el.x * 100}%`, top: `${el.y * 100}%`,
            width: `${el.width * 100}%`, height: `${el.height * 100}%`,
            zIndex: el.zIndex,
          }"
          :class="selectedKey === el.key && 'outline outline-2 outline-offset-2 outline-white'"
          @pointerdown="onElementPointerDown(el, $event)"
          @pointermove="onElementPointerMove"
          @pointerup="onElementPointerUp"
          @pointercancel="onElementPointerUp"
        >
          <div class="relative size-full overflow-hidden">
            <template v-if="el.mediaWidth && el.mediaHeight">
              <div :style="cropWrapperStyle(el)">
                <img
                  v-if="el.kind === 'image'"
                  :src="el.url" :alt="el.filename"
                  class="absolute max-w-none select-none"
                  :style="mediaStyle(el)"
                  draggable="false"
                />
                <video
                  v-else
                  :src="el.url"
                  class="absolute select-none"
                  :style="mediaStyle(el)"
                  :muted="!el.hasAudio"
                  loop playsinline autoplay draggable="false"
                />
              </div>
            </template>
            <div v-else class="flex size-full items-center justify-center bg-raised text-[11px] text-ink-subtle">
              {{ el.filename }}
            </div>
          </div>

          <div
            v-for="corner in CORNERS"
            v-show="selectedKey === el.key"
            :key="corner"
            class="absolute size-3 -translate-x-1/2 -translate-y-1/2 touch-none rounded-full border-2 border-ink bg-canvas"
            :style="{ left: HANDLE_POS[corner].left, top: HANDLE_POS[corner].top, cursor: HANDLE_CURSOR[corner] }"
            @pointerdown.stop="onHandlePointerDown(corner, $event)"
            @pointermove.stop="onHandlePointerMove"
            @pointerup.stop="onHandlePointerUp"
            @pointercancel.stop="onHandlePointerUp"
          />
        </div>

        <div v-if="!elements.length" class="flex size-full items-center justify-center text-[13px] text-white/40">
          Add an element to start this scene
        </div>
      </div>
    </div>

    <div v-if="selected" class="flex items-center justify-between gap-3 rounded-xl bg-surface p-3">
      <p class="min-w-0 truncate text-[13px] text-ink-muted">{{ selected.filename }}</p>
      <div class="flex shrink-0 items-center gap-2">
        <AppButton v-if="selected.kind === 'video'" variant="ghost" size="sm" @click="rotateSelected">
          Rotate ({{ selected.rotationDegrees }}°)
        </AppButton>
        <label v-if="selected.kind === 'video'" class="flex items-center gap-1.5 text-[13px] text-ink">
          <input v-model="selected.hasAudio" type="checkbox" class="size-3.5 accent-ink" />
          Sound
        </label>
        <AppButton variant="danger" size="sm" @click="deleteSelected">Delete</AppButton>
      </div>
    </div>

    <div class="flex justify-end gap-2">
      <AppButton variant="secondary" size="sm" @click="emit('close')">Cancel</AppButton>
      <AppButton size="sm" @click="apply">Apply</AppButton>
    </div>

    <AppModal v-if="picking" title="Add element" @close="picking = false">
      <p v-if="!library.length" class="text-sm text-ink-muted">
        The library is empty. Upload something on the Media page first.
      </p>
      <ul v-else class="max-h-80 overflow-y-auto">
        <li v-for="m in library" :key="m.id">
          <label class="flex cursor-pointer items-center gap-3 rounded-lg p-2 hover:bg-surface">
            <input
              type="checkbox"
              class="size-4 accent-ink"
              :checked="picked.has(m.id)"
              @change="togglePick(m.id)"
            />
            <div class="h-9 w-16 shrink-0 overflow-hidden rounded-md bg-raised">
              <img v-if="m.thumbnail_url" :src="m.thumbnail_url" :alt="m.filename"
                   class="size-full object-cover" />
            </div>
            <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ m.filename }}</span>
          </label>
        </li>
      </ul>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="picking = false">Cancel</AppButton>
        <AppButton size="sm" :disabled="!picked.size" @click="confirmPick">
          Add {{ picked.size || '' }}
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
