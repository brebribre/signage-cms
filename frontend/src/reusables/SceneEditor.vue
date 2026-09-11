<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconCheck from '~icons/material-symbols/check'
import IconCrop from '~icons/material-symbols/crop'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'
import IconImageOutline from '~icons/material-symbols/image-outline'
import IconKeyboardArrowDown from '~icons/material-symbols/keyboard-arrow-down'
import IconKeyboardArrowUp from '~icons/material-symbols/keyboard-arrow-up'
import IconLayersOutline from '~icons/material-symbols/layers-outline'
import IconRotateRight from '~icons/material-symbols/rotate-right'
import IconVideocam from '~icons/material-symbols/videocam'
import IconVolumeOff from '~icons/material-symbols/volume-off'
import IconVolumeUp from '~icons/material-symbols/volume-up'

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

/**
 * A full-page canvas editor for one scene: a left toolbar to bring media in, the canvas
 * itself to arrange it, and a right panel for whatever's selected. Deliberately kept
 * generic over "what a scene element is" — `library`/`DraftElement` both key off `kind`,
 * so a future iframe option is a new toolbar entry and a new branch in the right panel,
 * not a rewrite of the canvas or its drag/resize mechanics.
 */
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

const KIND_ICON = { image: IconImageOutline, video: IconVideocam } as const

function select(key: string | null) {
  selectedKey.value = key
}

// --- Layers: `elements`' own array order IS the stacking order (index -> zIndex), so the
// panel just lists it — front-most first, to match how layer panels read everywhere else —
// and reordering is a plain swap-and-reindex. ---

const layersTopFirst = computed(() => [...elements.value].reverse())

function reindexZ() {
  elements.value.forEach((e, i) => { e.zIndex = i })
}

function moveLayer(key: string, direction: 'up' | 'down') {
  const idx = elements.value.findIndex((e) => e.key === key)
  const swapWith = direction === 'up' ? idx + 1 : idx - 1
  if (idx === -1 || swapWith < 0 || swapWith >= elements.value.length) return
  const arr = elements.value
  ;[arr[idx], arr[swapWith]] = [arr[swapWith], arr[idx]]
  reindexZ()
}

// --- Canvas frame: same width-from-height-cap technique as ScreenPreview.vue, so the ratio
// is exact in both orientations. ---

const FRAME_MAX_HEIGHT = 640
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

// --- Crop mode: toggled per-selection, off by default. While on, dragging the element on
// the canvas pans the crop instead of moving the box. Leaving an element (deselect, or pick
// a new one) drops back to plain move so it's never a surprise on the next drag. ---

const cropMode = ref(false)
watch(selectedKey, () => { cropMode.value = false })

// --- Drag an element to move it (or, in crop mode, to pan its crop). Same technique as the
// crop pan this session already proved: track pointer delta against the dragged element's
// OWN rendered box, never the canvas or the rotated media inside it, so the math is exactly
// the same at every rotation and every zoom. ---

const dragging = ref(false)
let dragStartPointer = { x: 0, y: 0 }
let dragStartBox = { x: 0, y: 0, cropX: 0.5, cropY: 0.5 }
let dragElementRect: DOMRect | null = null

function elementTargetAspect(el: DraftElement): number {
  return (el.width / el.height) * canvasAspect.value
}

function currentCropRect(el: DraftElement, cx: number, cy: number) {
  const eff = effectiveDimensions(el.mediaWidth ?? 1, el.mediaHeight ?? 1, el.rotationDegrees)
  return resolveCropRect(eff.width, eff.height, elementTargetAspect(el), cx, cy, el.cropZoom ?? 1)
}

function onElementPointerDown(el: DraftElement, e: PointerEvent) {
  select(el.key)
  dragging.value = true
  dragStartPointer = { x: e.clientX, y: e.clientY }
  dragStartBox = { x: el.x, y: el.y, cropX: el.cropX ?? 0.5, cropY: el.cropY ?? 0.5 }
  dragElementRect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onElementPointerMove(e: PointerEvent) {
  if (!dragging.value || !selected.value) return

  if (cropMode.value && selected.value.mediaWidth && selected.value.mediaHeight && dragElementRect) {
    // Pan: the crop rect's own on-screen box is dragElementRect, so a pixel delta there
    // converts straight to a fraction of the crop rect's normalized (media-space) size —
    // dragging the image itself, not the window looking at it, so the sign is inverted.
    const rect = currentCropRect(selected.value, dragStartBox.cropX, dragStartBox.cropY)
    const dxFrac = (e.clientX - dragStartPointer.x) / dragElementRect.width
    const dyFrac = (e.clientY - dragStartPointer.y) / dragElementRect.height
    selected.value.cropX = dragStartBox.cropX - dxFrac * rect.w
    selected.value.cropY = dragStartBox.cropY - dyFrac * rect.h
    return
  }

  if (!canvasRef.value) return
  const box = canvasRef.value.getBoundingClientRect()
  selected.value.x = dragStartBox.x + (e.clientX - dragStartPointer.x) / box.width
  selected.value.y = dragStartBox.y + (e.clientY - dragStartPointer.y) / box.height
}

function onElementPointerUp(e: PointerEvent) {
  dragging.value = false
  dragElementRect = null
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

// --- Crop via edge handles — shown only in crop mode, in place of the corner handles.
// Dragging one edge moves just that edge (the opposite edge stays put), same anchor logic
// as the corner resize but locked to a single axis. The box's aspect changes as a result,
// and since the box's own aspect is what the cover-crop math targets, trimming an edge is
// exactly what crops the media — no separate crop rectangle to keep in sync. -->

type Edge = 'n' | 's' | 'e' | 'w'
const EDGES: Edge[] = ['n', 's', 'e', 'w']

const resizingEdge = ref<Edge | null>(null)
let edgeStartPointer = { x: 0, y: 0 }
let edgeStartBox = { x: 0, y: 0, width: 0, height: 0 }

function onEdgeHandlePointerDown(edge: Edge, e: PointerEvent) {
  if (!selected.value) return
  resizingEdge.value = edge
  edgeStartPointer = { x: e.clientX, y: e.clientY }
  edgeStartBox = {
    x: selected.value.x, y: selected.value.y,
    width: selected.value.width, height: selected.value.height,
  }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onEdgeHandlePointerMove(e: PointerEvent) {
  if (!resizingEdge.value || !selected.value || !canvasRef.value) return
  const box = canvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - edgeStartPointer.x) / box.width
  const dy = (e.clientY - edgeStartPointer.y) / box.height
  let { x, y, width, height } = edgeStartBox
  const edge = resizingEdge.value
  if (edge === 'e') width += dx
  else if (edge === 'w') { x += dx; width -= dx }
  else if (edge === 's') height += dy
  else if (edge === 'n') { y += dy; height -= dy }
  selected.value.x = x
  selected.value.y = y
  selected.value.width = Math.max(MIN_SIZE, width)
  selected.value.height = Math.max(MIN_SIZE, height)
}

function onEdgeHandlePointerUp(e: PointerEvent) {
  resizingEdge.value = null
  releaseCapture(e)
}

const EDGE_POS: Record<Edge, { left: string; top: string }> = {
  n: { left: '50%', top: '0%' },
  s: { left: '50%', top: '100%' },
  w: { left: '0%', top: '50%' },
  e: { left: '100%', top: '50%' },
}
const EDGE_CURSOR: Record<Edge, string> = { n: 'ns-resize', s: 'ns-resize', e: 'ew-resize', w: 'ew-resize' }

// --- Rendering: an element's own box (x/y/width/height, as a fraction of the canvas) sets
// the target aspect ratio; resizing the box *is* the crop, and cropX/cropY/cropZoom pan and
// zoom within it. ---

function cropWrapperStyle(el: DraftElement) {
  if (!el.mediaWidth || !el.mediaHeight) return {}
  const rect = currentCropRect(el, el.cropX ?? 0.5, el.cropY ?? 0.5)
  return { position: 'absolute' as const, ...cropRectToStyle(rect), ...ROTATION_WRAPPER_STYLE }
}

function mediaStyle(el: DraftElement) {
  return rotationStyle(el.rotationDegrees)
}

// --- Right panel: rotate, crop (pan on-canvas + zoom here), mute/unmute for video, delete. ---

/** Rotating 90°/270° swaps what's tall and what's wide, so the box swaps with it — a
 *  centered swap, not just a resize, so the box doesn't jump. Without this, a wide box stays
 *  wide after rotating its content upright, cropping most of it away against the now-mismatched
 *  aspect ratio. */
function rotateSelected() {
  const el = selected.value
  if (!el) return
  const cx = el.x + el.width / 2
  const cy = el.y + el.height / 2
  ;[el.width, el.height] = [el.height, el.width]
  el.x = cx - el.width / 2
  el.y = cy - el.height / 2
  el.rotationDegrees = (el.rotationDegrees + 90) % 360
}

function onZoomInput(e: Event) {
  if (!selected.value) return
  selected.value.cropZoom = Number((e.target as HTMLInputElement).value)
}

function resetCrop() {
  if (!selected.value) return
  selected.value.cropX = null
  selected.value.cropY = null
  selected.value.cropZoom = null
}

function deleteSelected() {
  if (!selectedKey.value) return
  elements.value = elements.value.filter((e) => e.key !== selectedKey.value)
  selectedKey.value = null
}

// --- Add element: from the left toolbar, either a click (stacked, staggered placement) or
// a drag onto the canvas (placed under the pointer). Both funnel through the same helper so
// a future "Create custom" source (e.g. iframe) only needs its own toolbar entry. ---

let addStagger = 0

/** A new element's box matches the media's own aspect ratio (capped to a reasonable size),
 *  so `elementTargetAspect` starts out equal to the media's — the cover-crop math in
 *  `currentCropRect` then resolves to the full, uncropped image. Anything cropped from here
 *  on is something the person actually did (a resize, an edge-crop drag), not a surprise
 *  from a mismatched default box. */
function defaultBoxSize(m: MediaRead): { width: number; height: number } {
  const MAX = 0.6
  const mediaAspect = m.width && m.height ? m.width / m.height : 1
  const boxRatio = mediaAspect / canvasAspect.value
  return boxRatio >= 1
    ? { width: MAX, height: MAX / boxRatio }
    : { width: MAX * boxRatio, height: MAX }
}

function addFromMedia(m: MediaRead, at?: { x: number; y: number }) {
  const { width, height } = defaultBoxSize(m)
  const maxZ = Math.max(0, ...elements.value.map((e) => e.zIndex))
  const x = at
    ? Math.min(Math.max(at.x - width / 2, 0), 1 - width)
    : Math.min(0.3 + addStagger, 1 - width)
  const y = at
    ? Math.min(Math.max(at.y - height / 2, 0), 1 - height)
    : Math.min(0.3 + addStagger, 1 - height)
  if (!at) addStagger = (addStagger + 0.03) % 0.15
  const el = mediaToDraftElement(m, { x, y, width, height, zIndex: maxZ + 1 })
  elements.value.push(el)
  select(el.key)
}

function onToolbarDragStart(m: MediaRead, e: DragEvent) {
  e.dataTransfer?.setData('text/plain', m.id)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy'
}

function onCanvasDrop(e: DragEvent) {
  const id = e.dataTransfer?.getData('text/plain')
  const media = props.library.find((m) => m.id === id)
  if (!media || !canvasRef.value) return
  const box = canvasRef.value.getBoundingClientRect()
  addFromMedia(media, {
    x: (e.clientX - box.left) / box.width,
    y: (e.clientY - box.top) / box.height,
  })
}

function apply() {
  emit('apply', elements.value)
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 items-center justify-between gap-4 border-b border-line px-4 py-3 sm:px-6">
      <div class="flex min-w-0 items-center gap-3">
        <AppButton variant="ghost" size="sm" @click="emit('close')">
          <IconArrowBack class="size-4" />
          Back
        </AppButton>
        <div class="min-w-0">
          <p class="truncate text-sm text-ink">Scene</p>
          <p class="truncate text-[13px] text-ink-subtle">For {{ referenceScreen.label }}</p>
        </div>
      </div>
      <AppButton size="sm" @click="apply">
        <IconCheck class="size-4" />
        Apply
      </AppButton>
    </div>

    <div class="flex min-h-0 flex-1">
      <!-- Left toolbar -->
      <aside class="flex w-60 shrink-0 flex-col overflow-y-auto border-r border-line p-3">
        <p class="mb-2 px-1 text-[13px] text-ink-subtle">Add media</p>
        <p v-if="!library.length" class="px-1 text-[13px] text-ink-muted">
          The library is empty. Upload something on the Media page first.
        </p>
        <ul v-else class="flex flex-col gap-1">
          <li v-for="m in library" :key="m.id">
            <div
              draggable="true"
              class="flex cursor-grab items-center gap-2.5 rounded-lg p-1.5 transition-colors
                     duration-200 hover:bg-surface active:cursor-grabbing"
              title="Drag onto the canvas, or click to add"
              @dragstart="onToolbarDragStart(m, $event)"
              @click="addFromMedia(m)"
            >
              <div class="relative h-10 w-16 shrink-0 overflow-hidden rounded-md bg-raised">
                <img
                  v-if="m.thumbnail_url"
                  :src="m.thumbnail_url" :alt="m.filename"
                  class="size-full object-cover" draggable="false"
                />
                <component
                  :is="KIND_ICON[m.kind]"
                  class="absolute bottom-1 right-1 size-3.5 text-white/90"
                />
              </div>
              <span class="min-w-0 flex-1 truncate text-[13px] text-ink">{{ m.filename }}</span>
            </div>
          </li>
        </ul>
      </aside>

      <!-- Canvas -->
      <div
        class="flex min-w-0 flex-1 items-center justify-center overflow-auto bg-surface p-6"
        @click.self="select(null)"
      >
        <div class="flex justify-center" :style="frameOuterStyle" @click.self="select(null)">
          <div
            ref="canvasRef"
            class="relative w-full overflow-hidden rounded-xl bg-black"
            :style="frameStyle"
            @click.self="select(null)"
            @dragover.prevent
            @drop.prevent="onCanvasDrop"
          >
            <div
              v-for="el in elements"
              :key="el.key"
              class="absolute touch-none select-none"
              :class="[
                cropMode && selectedKey === el.key ? 'cursor-move' : 'cursor-grab active:cursor-grabbing',
                selectedKey === el.key && 'outline outline-2 outline-offset-2 outline-white',
              ]"
              :style="{
                left: `${el.x * 100}%`, top: `${el.y * 100}%`,
                width: `${el.width * 100}%`, height: `${el.height * 100}%`,
                zIndex: el.zIndex,
              }"
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
                v-show="selectedKey === el.key && !cropMode"
                :key="corner"
                class="absolute size-3 -translate-x-1/2 -translate-y-1/2 touch-none rounded-full border-2 border-ink bg-canvas"
                :style="{ left: HANDLE_POS[corner].left, top: HANDLE_POS[corner].top, cursor: HANDLE_CURSOR[corner] }"
                @pointerdown.stop="onHandlePointerDown(corner, $event)"
                @pointermove.stop="onHandlePointerMove"
                @pointerup.stop="onHandlePointerUp"
                @pointercancel.stop="onHandlePointerUp"
              />

              <!-- Crop handles: thicker bars at each edge's midpoint, the common-software
                   crop tell — drag one inward to trim that side. -->
              <div
                v-for="edge in EDGES"
                v-show="selectedKey === el.key && cropMode"
                :key="edge"
                class="absolute -translate-x-1/2 -translate-y-1/2 touch-none rounded-full border-2 border-ink bg-canvas"
                :class="edge === 'n' || edge === 's' ? 'h-1.5 w-8' : 'h-8 w-1.5'"
                :style="{ left: EDGE_POS[edge].left, top: EDGE_POS[edge].top, cursor: EDGE_CURSOR[edge] }"
                @pointerdown.stop="onEdgeHandlePointerDown(edge, $event)"
                @pointermove.stop="onEdgeHandlePointerMove"
                @pointerup.stop="onEdgeHandlePointerUp"
                @pointercancel.stop="onEdgeHandlePointerUp"
              />
            </div>

            <div v-if="!elements.length" class="flex size-full items-center justify-center px-6 text-center text-[13px] text-white/40">
              Drag media from the left, or click it, to start this scene
            </div>
          </div>
        </div>
      </div>

      <!-- Right panel: layers on top, details for whatever's selected below -->
      <aside class="flex w-72 shrink-0 flex-col overflow-y-auto border-l border-line">
        <div v-if="elements.length" class="flex max-h-56 shrink-0 flex-col gap-0.5 overflow-y-auto border-b border-line p-3">
          <p class="mb-1 flex items-center gap-1.5 px-1 text-[13px] text-ink-subtle">
            <IconLayersOutline class="size-3.5" />
            Layers
          </p>
          <div
            v-for="(el, idx) in layersTopFirst"
            :key="el.key"
            class="flex cursor-pointer items-center gap-2 rounded-lg p-1.5 transition-colors duration-150"
            :class="selectedKey === el.key ? 'bg-raised' : 'hover:bg-surface'"
            @click="select(el.key)"
          >
            <div class="relative h-8 w-12 shrink-0 overflow-hidden rounded-md bg-raised">
              <img
                v-if="el.thumbnailUrl"
                :src="el.thumbnailUrl" :alt="el.filename"
                class="size-full object-cover"
              />
              <component :is="KIND_ICON[el.kind]" class="absolute bottom-0.5 right-0.5 size-3 text-white/90" />
            </div>
            <span class="min-w-0 flex-1 truncate text-[13px] text-ink">{{ el.filename }}</span>
            <div class="flex shrink-0 flex-col">
              <button
                type="button" class="text-ink-subtle hover:text-ink disabled:pointer-events-none disabled:opacity-30"
                :disabled="idx === 0"
                @click.stop="moveLayer(el.key, 'up')"
              >
                <IconKeyboardArrowUp class="size-4" />
              </button>
              <button
                type="button" class="text-ink-subtle hover:text-ink disabled:pointer-events-none disabled:opacity-30"
                :disabled="idx === layersTopFirst.length - 1"
                @click.stop="moveLayer(el.key, 'down')"
              >
                <IconKeyboardArrowDown class="size-4" />
              </button>
            </div>
          </div>
        </div>

        <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
          <template v-if="selected">
            <div class="flex items-center gap-2">
              <component :is="KIND_ICON[selected.kind]" class="size-4 shrink-0 text-ink-subtle" />
              <p class="min-w-0 truncate text-sm text-ink">{{ selected.filename }}</p>
            </div>

            <div class="flex flex-col gap-2">
              <p class="text-[13px] text-ink-subtle">Transform</p>
              <div class="flex flex-wrap gap-2">
                <AppButton variant="secondary" size="sm" @click="rotateSelected">
                  <IconRotateRight class="size-4" />
                  Rotate
                </AppButton>
                <AppButton
                  :variant="cropMode ? 'primary' : 'secondary'" size="sm"
                  :disabled="!selected.mediaWidth"
                  @click="cropMode = !cropMode"
                >
                  <IconCrop class="size-4" />
                  Crop
                </AppButton>
                <AppButton
                  v-if="selected.kind === 'video'"
                  variant="secondary" size="sm"
                  @click="selected.hasAudio = !selected.hasAudio"
                >
                  <component :is="selected.hasAudio ? IconVolumeUp : IconVolumeOff" class="size-4" />
                  {{ selected.hasAudio ? 'Mute' : 'Unmute' }}
                </AppButton>
              </div>
            </div>

            <div v-if="cropMode" class="flex flex-col gap-2 rounded-xl bg-surface p-3">
              <p class="text-[13px] text-ink-subtle">
                Drag an edge to crop that side, or the middle to pan
              </p>
              <div class="flex items-center gap-2">
                <input
                  type="range" min="1" max="3" step="0.05"
                  :value="selected.cropZoom ?? 1"
                  class="h-1.5 w-full cursor-pointer accent-ink"
                  @input="onZoomInput"
                />
                <span class="w-11 shrink-0 text-right text-[13px] text-ink-muted">
                  {{ (selected.cropZoom ?? 1).toFixed(2) }}×
                </span>
              </div>
              <AppButton variant="ghost" size="sm" class="self-start" @click="resetCrop">Reset crop</AppButton>
            </div>

            <AppButton variant="danger" size="sm" class="mt-auto self-start" @click="deleteSelected">
              <IconDeleteOutline class="size-4" />
              Delete
            </AppButton>
          </template>
          <p v-else class="text-[13px] text-ink-subtle">Select an item on the canvas to edit it.</p>
        </div>
      </aside>
    </div>
  </div>
</template>
