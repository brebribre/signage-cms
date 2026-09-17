<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconAspectRatio from '~icons/material-symbols/aspect-ratio-outline'
import IconClose from '~icons/material-symbols/close'
import IconWallpaper from '~icons/material-symbols/wallpaper'
import IconCheck from '~icons/material-symbols/check'
import IconCrop from '~icons/material-symbols/crop'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'
import IconImageOutline from '~icons/material-symbols/image-outline'
import IconKeyboardArrowDown from '~icons/material-symbols/keyboard-arrow-down'
import IconKeyboardArrowUp from '~icons/material-symbols/keyboard-arrow-up'
import IconLanguage from '~icons/material-symbols/language'
import IconLayersOutline from '~icons/material-symbols/layers-outline'
import IconAddPhotoAlternateOutline from '~icons/material-symbols/add-photo-alternate-outline'
import IconPhotoLibraryOutline from '~icons/material-symbols/photo-library-outline'
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
import { mediaToDraftElement, websiteToDraftElement } from '@/hooks/usePlaylistEditor'
import { websiteLayoutScreen } from '@/utils/websiteLayout'
import { normalizeWebsiteUrl, websiteLabel } from '@/utils/websiteUrl'
import type { DraftElement, DraftItem } from '@/hooks/usePlaylistEditor'
import type { MediaRead, SceneBackground } from '@/types/api'
import { BLUR_IMAGE_STYLE, SCENE_BACKGROUNDS, blurImageUrl, blurSource } from '@/utils/sceneBackground'
import { useMediaUpload } from '@/hooks/useMediaUpload'
import AppButton from '@/reusables/AppButton.vue'
import UploadStatus from '@/reusables/UploadStatus.vue'

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
  apply: [elements: DraftElement[], background: SceneBackground]
  close: []
  /** A file uploaded from inside the scene still belongs in the library — the page that owns
   *  it prepends, so it is there next time without a refetch. */
  uploaded: [media: MediaRead]
}>()

/** Uploading from in here adds to the canvas as well as the library: you went looking for
 *  "add media" while building a scene, so the file you just picked is wanted *in* the scene.
 *  Before this, an empty library dead-ended with "upload something on the Media page first",
 *  which means leaving a half-built scene to do it. */
const { jobs: uploadJobs, add: addUploads } = useMediaUpload((media) => {
  emit('uploaded', media)
  addFromMedia(media)
})
const mediaInput = ref<HTMLInputElement | null>(null)

function onMediaFiles(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) addUploads(input.files)
  input.value = ''
}

/** Depth-counted — see MediaPicker for why a boolean flickers. */
let panelDragDepth = 0
const isPanelDragOver = ref(false)
function onPanelDragEnter() {
  panelDragDepth++
  isPanelDragOver.value = true
}
function onPanelDragLeave() {
  panelDragDepth--
  if (panelDragDepth <= 0) isPanelDragOver.value = false
}
function onPanelDrop(e: DragEvent) {
  panelDragDepth = 0
  isPanelDragOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (!files.length) return // an element being dragged within the editor, not a file
  panel.value = 'media'
  addUploads(files)
}

// A local working copy — nothing here reaches the draft scene until Apply.
const elements = ref<DraftElement[]>(props.item.elements.map((e) => ({ ...e })))
const background = ref<SceneBackground>(props.item.background)
const blurUrl = computed(() => {
  if (background.value !== 'blur') return null
  const source = blurSource(elements.value)
  return source ? blurImageUrl(source) : null
})
const selectedKey = ref<string | null>(null)
const selected = computed(() => elements.value.find((e) => e.key === selectedKey.value) ?? null)

const KIND_ICON = { image: IconImageOutline, video: IconVideocam, web: IconLanguage } as const

/** The left rail, Canva-style: pick a source, its panel opens beside it. Two for now; another
 *  source is one more entry here and one more branch in the panel below. */
const PANELS = [
  { id: 'media', label: 'Media', icon: IconPhotoLibraryOutline },
  { id: 'website', label: 'Website', icon: IconLanguage },
] as const
type PanelId = (typeof PANELS)[number]['id']
const panel = ref<PanelId>('media')

/** Filters the library by filename — a signage library gets long, and hunting one logo down a
 *  scrolling list is the slowest part of building a scene. */
const mediaQuery = ref('')
const filteredLibrary = computed(() => {
  const q = mediaQuery.value.trim().toLowerCase()
  return q ? props.library.filter((m) => m.filename.toLowerCase().includes(q)) : props.library
})

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
/** The canvas fits the stage it sits in both ways — on a phone a portrait screen is limited by
 *  the height left between the header and the toolbar, not just the width. */
const stageRef = ref<HTMLElement | null>(null)
const stageSize = ref({ width: 0, height: 0 })
const frameWidthPx = computed(() => {
  const byCap = FRAME_MAX_HEIGHT * canvasAspect.value
  const { width, height } = stageSize.value
  if (!width || !height) return Math.round(byCap)
  return Math.max(0, Math.round(Math.min(byCap, width, height * canvasAspect.value)))
})
const frameOuterStyle = computed(() => ({ width: `min(100%, ${frameWidthPx.value}px)` }))
let stageObserver: ResizeObserver | null = null
const lockedScrollers: { el: HTMLElement; overflow: string; overscroll: string }[] = []
onMounted(() => {
  for (const el of [document.documentElement, document.body, document.getElementById('main')]) {
    if (!el) continue
    lockedScrollers.push({ el, overflow: el.style.overflow, overscroll: el.style.overscrollBehavior })
    el.style.overflow = 'hidden'
    el.style.overscrollBehavior = 'none'
  }
})
onUnmounted(() => {
  for (const { el, overflow, overscroll } of lockedScrollers.splice(0)) {
    el.style.overflow = overflow
    el.style.overscrollBehavior = overscroll
  }
})
onMounted(() => {
  stageObserver = new ResizeObserver(([entry]) => {
    const style = getComputedStyle(entry.target)
    const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
    const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
    const box = entry.target.getBoundingClientRect()
    stageSize.value = { width: box.width - padX, height: box.height - padY }
  })
  if (stageRef.value) stageObserver.observe(stageRef.value)
})
onUnmounted(() => stageObserver?.disconnect())

// --- Phones and tablets (below lg): Canva's mobile layout. The canvas takes the screen, a toolbar
// along the bottom holds the tools — the sources when nothing is selected, what you can do to
// the selection when something is — and the desktop side panels open as bottom sheets. ---

const wideQuery = typeof window !== 'undefined' ? window.matchMedia('(min-width: 1024px)') : null
const isWide = ref(wideQuery?.matches ?? true)
function onWideChange(e: MediaQueryListEvent) {
  isWide.value = e.matches
  if (e.matches) sheet.value = null
}
onMounted(() => wideQuery?.addEventListener('change', onWideChange))
onUnmounted(() => wideQuery?.removeEventListener('change', onWideChange))

/** Which bottom sheet is open on a narrow screen: a source panel, or the edit panel (layers,
 *  background, and the selection's details). */
const sheet = ref<'sources' | 'edit' | null>(null)
function openSources(id: PanelId) {
  panel.value = id
  sheet.value = 'sources'
}
function closeSheet() {
  sheet.value = null
}
const frameStyle = computed(() => ({
  aspectRatio: `${props.referenceScreen.width} / ${props.referenceScreen.height}`,
}))

const canvasRef = ref<HTMLElement | null>(null)

// A website is laid out at the reference screen's real pixel size and scaled down with the
// canvas — same as ScreenPreview.vue — so it shows the layout the screen will.
const canvasWidth = ref(0)
let canvasObserver: ResizeObserver | null = null
onMounted(() => {
  canvasObserver = new ResizeObserver(() => {
    canvasWidth.value = canvasRef.value?.clientWidth ?? 0
  })
  if (canvasRef.value) canvasObserver.observe(canvasRef.value)
})
onUnmounted(() => canvasObserver?.disconnect())

// --- Floating controls on the canvas, Canva-style: a pill with Delete above the selected element
// and a round Rotate button below it. They go on the other side when there isn't room, sit inside
// the element when there's room on neither side, and are held on the canvas horizontally. Hidden
// while the element is being dragged, resized or cropped, so they never get in the way. ---

const FLOAT_GAP = 12
/** Height a floating control needs, plus its gap — room required on a side before it goes there. */
const FLOAT_ROOM = 48
const floatingHidden = computed(() => dragging.value || !!resizingCorner.value || !!resizingEdge.value || cropMode.value)

const floating = computed(() => {
  const el = selected.value
  const width = canvasWidth.value
  if (!el || !width) return null
  const height = width / canvasAspect.value
  const top = el.y * height
  const bottom = (el.y + el.height) * height
  const center = Math.min(Math.max((el.x + el.width / 2) * width, 28), width - 28)
  const roomAbove = top >= FLOAT_ROOM
  const roomBelow = height - bottom >= FLOAT_ROOM

  type Place = { left: string; top: string; transform: string }
  const above = (stack: number): Place => ({ left: `${center}px`, top: `${top}px`, transform: `translate(-50%, calc(-100% - ${FLOAT_GAP + stack}px))` })
  const below = (stack: number): Place => ({ left: `${center}px`, top: `${bottom}px`, transform: `translate(-50%, ${FLOAT_GAP + stack}px)` })

  let pill: Place
  let rotate: Place
  if (roomAbove || roomBelow) {
    // Both on one side when only one side has room: the rotate button nearest, the pill beyond it.
    pill = roomAbove ? above(0) : below(FLOAT_ROOM)
    rotate = roomBelow ? below(0) : above(FLOAT_ROOM)
  } else {
    // An element taller than the canvas: keep both inside it, at its visible top and bottom.
    pill = { left: `${center}px`, top: `${Math.max(top, 0)}px`, transform: `translate(-50%, ${FLOAT_GAP}px)` }
    rotate = { left: `${center}px`, top: `${Math.min(bottom, height)}px`, transform: `translate(-50%, calc(-100% - ${FLOAT_GAP}px))` }
  }
  return { pill, rotate }
})

function webFrameStyle(el: DraftElement) {
  const { width, height } = websiteLayoutScreen(props.referenceScreen.width, props.referenceScreen.height)
  return {
    width: `${width * el.width}px`,
    height: `${height * el.height}px`,
    transform: `scale(${canvasWidth.value / width})`,
  }
}

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

// --- Handles, the way Canva's work: a CORNER scales the element, keeping its shape; a SIDE
// crops that side. Both anchor on the opposite corner/side, so what you aren't dragging stays
// exactly where it was. ---

type Corner = 'nw' | 'ne' | 'sw' | 'se'
const CORNERS: Corner[] = ['nw', 'ne', 'sw', 'se']
const MIN_SIZE = 0.05
/** The server's cap on crop zoom (services/playlists.py MAX_CROP_ZOOM) — a side can't crop
 *  tighter than this, or the scene would fail to save. */
const MAX_CROP_ZOOM = 3

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

/** Proportional scale about the opposite corner. Worked in a single scale factor — whichever
 *  axis the pointer has moved further along — so the box's aspect never drifts, and neither does
 *  the media's crop inside it (the same crop at the same aspect is the same picture, larger). */
function onHandlePointerMove(e: PointerEvent) {
  if (!resizingCorner.value || !selected.value || !canvasRef.value) return
  const canvas = canvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - resizeStartPointer.x) / canvas.width
  const dy = (e.clientY - resizeStartPointer.y) / canvas.height
  const corner = resizingCorner.value
  const sx = corner === 'ne' || corner === 'se' ? 1 : -1
  const sy = corner === 'sw' || corner === 'se' ? 1 : -1
  const start = resizeStartBox
  const scale = Math.max(
    (start.width + sx * dx) / start.width,
    (start.height + sy * dy) / start.height,
    MIN_SIZE / Math.min(start.width, start.height),
  )
  const width = start.width * scale
  const height = start.height * scale
  selected.value.width = width
  selected.value.height = height
  selected.value.x = sx === 1 ? start.x : start.x + start.width - width
  selected.value.y = sy === 1 ? start.y : start.y + start.height - height
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

type Edge = 'n' | 's' | 'e' | 'w'
const EDGES: Edge[] = ['n', 's', 'e', 'w']

const resizingEdge = ref<Edge | null>(null)
let edgeStartPointer = { x: 0, y: 0 }
let edgeStartBox = { x: 0, y: 0, width: 0, height: 0 }
/** Where the whole media sits on the canvas (fractions), cropped parts included — held fixed for
 *  the length of a side-crop drag. Null for a website, which has nothing to crop. */
let edgeMedia: { left: number; top: number; width: number; height: number } | null = null

/**
 * A Fit (or legacy Stretch) element shows its media letterboxed inside a larger box. Cropping
 * starts from what is actually visible, so the box first shrinks onto the media and becomes
 * Fill — which looks the same, minus the bars — and the crop proceeds from there.
 */
function fillToVisibleMedia(el: DraftElement) {
  if (el.fit === 'cover' || !el.mediaWidth || !el.mediaHeight) return
  const eff = effectiveDimensions(el.mediaWidth, el.mediaHeight, el.rotationDegrees)
  const mediaAspect = eff.width / eff.height
  if (el.fit === 'contain') {
    if (mediaAspect > elementTargetAspect(el)) {
      const height = (el.width * canvasAspect.value) / mediaAspect
      el.y += (el.height - height) / 2
      el.height = height
    } else {
      const width = (el.height * mediaAspect) / canvasAspect.value
      el.x += (el.width - width) / 2
      el.width = width
    }
  }
  el.fit = 'cover'
  el.cropX = 0.5
  el.cropY = 0.5
  el.cropZoom = 1
}

function onEdgeHandlePointerDown(edge: Edge, e: PointerEvent) {
  const el = selected.value
  if (!el) return
  edgeMedia = null
  if (el.mediaWidth && el.mediaHeight) {
    fillToVisibleMedia(el)
    const rect = currentCropRect(el, el.cropX ?? 0.5, el.cropY ?? 0.5)
    const width = el.width / rect.w
    const height = el.height / rect.h
    edgeMedia = { left: el.x - rect.x * width, top: el.y - rect.y * height, width, height }
  }
  resizingEdge.value = edge
  edgeStartPointer = { x: e.clientX, y: e.clientY }
  edgeStartBox = { x: el.x, y: el.y, width: el.width, height: el.height }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

/**
 * Moves one side, the opposite one staying put.
 *
 * For media it is a crop: the picture stays exactly where it is on the canvas and only the window
 * onto it moves — so the side can go back out, revealing what was cropped, up to the media's own
 * edge and no further. The new window is then written back as the element's box plus the
 * crop centre and zoom that reproduce it (resolveCropRect's inverse). A website has no picture
 * to hold still, so its side simply resizes that side.
 */
function onEdgeHandlePointerMove(e: PointerEvent) {
  const el = selected.value
  if (!resizingEdge.value || !el || !canvasRef.value) return
  const canvas = canvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - edgeStartPointer.x) / canvas.width
  const dy = (e.clientY - edgeStartPointer.y) / canvas.height
  const edge = resizingEdge.value
  const start = edgeStartBox

  let left = start.x
  let top = start.y
  let right = start.x + start.width
  let bottom = start.y + start.height
  const m = edgeMedia
  const minLeft = m ? m.left : -Infinity
  const maxRight = m ? m.left + m.width : Infinity
  const minTop = m ? m.top : -Infinity
  const maxBottom = m ? m.top + m.height : Infinity
  if (edge === 'e') right = Math.min(maxRight, Math.max(left + MIN_SIZE, right + dx))
  else if (edge === 'w') left = Math.max(minLeft, Math.min(right - MIN_SIZE, left + dx))
  else if (edge === 's') bottom = Math.min(maxBottom, Math.max(top + MIN_SIZE, bottom + dy))
  else top = Math.max(minTop, Math.min(bottom - MIN_SIZE, top + dy))

  const box = { x: left, y: top, width: right - left, height: bottom - top }
  if (!m || !el.mediaWidth || !el.mediaHeight) {
    Object.assign(el, box)
    return
  }

  // The visible window as a fraction of the media, and the zoom resolveCropRect needs to produce
  // a window that size at this box's aspect.
  const w = box.width / m.width
  const h = box.height / m.height
  const eff = effectiveDimensions(el.mediaWidth, el.mediaHeight, el.rotationDegrees)
  const mediaAspect = eff.width / eff.height
  const boxAspect = (box.width / box.height) * canvasAspect.value
  const fullWindowW = mediaAspect > boxAspect ? boxAspect / mediaAspect : 1
  const zoom = Math.max(1, fullWindowW / w)
  if (zoom > MAX_CROP_ZOOM) return // cropped as far as a scene can be

  Object.assign(el, box)
  el.cropZoom = zoom
  el.cropX = (box.x - m.left) / m.width + w / 2
  el.cropY = (box.y - m.top) / m.height + h / 2
}

function onEdgeHandlePointerUp(e: PointerEvent) {
  resizingEdge.value = null
  edgeMedia = null
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
  if (el.fit !== 'cover') return { position: 'absolute' as const, inset: 0, ...ROTATION_WRAPPER_STYLE }
  const rect = currentCropRect(el, el.cropX ?? 0.5, el.cropY ?? 0.5)
  return { position: 'absolute' as const, ...cropRectToStyle(rect), ...ROTATION_WRAPPER_STYLE }
}

function mediaStyle(el: DraftElement) {
  if (el.fit === 'cover') return rotationStyle(el.rotationDegrees)
  return { ...rotationStyle(el.rotationDegrees), objectFit: el.fit === 'stretch' ? 'fill' : 'contain' } as const
}

/** Fit shows the whole media inside its box (letterboxed, with the scene background showing
 *  through); Fill covers the box and can be cropped. Stretch isn't offered here — it only
 *  exists for older data — but an element that has it keeps it until switched. */
function setFit(fit: 'contain' | 'cover') {
  if (!selected.value) return
  selected.value.fit = fit
  if (fit !== 'cover') cropMode.value = false
}

// --- Right panel: rotate, crop (pan on-canvas + zoom here), mute/unmute for video, delete. ---

/** A quarter turn clockwise, like turning the picture on the table: the same size, around its own
 *  centre.
 *
 *  The box's width and height are fractions of the canvas's width and height, and the canvas isn't
 *  square — so swapping the two *fractions* would change the box's real size and shape (a 16:9
 *  screen made every rotated box smaller and squarer). What swaps is the real length: the new width
 *  is the old height measured against the canvas width, and vice versa. The crop turns with the
 *  picture, so the same part of it stays in view. */
function rotateSelected() {
  const el = selected.value
  if (!el) return
  const aspect = canvasAspect.value
  const cx = el.x + el.width / 2
  const cy = el.y + el.height / 2
  const width = el.height / aspect
  const height = el.width * aspect
  el.width = width
  el.height = height
  el.x = cx - width / 2
  el.y = cy - height / 2
  // A point at (x, y) in the picture as shown sits at (1 − y, x) after a clockwise quarter turn.
  if (el.cropX != null || el.cropY != null) {
    const cropX = el.cropX ?? 0.5
    const cropY = el.cropY ?? 0.5
    el.cropX = 1 - cropY
    el.cropY = cropX
  }
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
  if (!isWide.value) closeSheet()
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
  if (!isWide.value) closeSheet()
}

// --- Websites: added from the toolbar's address field, and re-pointed from the right panel. ---

const websiteInput = ref('')
const websiteError = ref<string | null>(null)

function addWebsite() {
  const url = normalizeWebsiteUrl(websiteInput.value)
  if (!url) {
    websiteError.value = 'Enter a full https:// address'
    return
  }
  websiteError.value = null
  websiteInput.value = ''
  const size = 0.6
  const maxZ = Math.max(0, ...elements.value.map((e) => e.zIndex))
  const offset = Math.min(0.2 + addStagger, 1 - size)
  addStagger = (addStagger + 0.03) % 0.15
  const el = websiteToDraftElement(url, { x: offset, y: offset, width: size, height: size, zIndex: maxZ + 1 })
  elements.value.push(el)
  select(el.key)
  if (!isWide.value) closeSheet()
}

const selectedUrlDraft = ref('')
const selectedUrlError = ref<string | null>(null)
watch(selectedKey, () => {
  selectedUrlDraft.value = selected.value?.webUrl ?? ''
  selectedUrlError.value = null
})

function onSelectedUrlCommit() {
  const el = selected.value
  if (!el || el.kind !== 'web') return
  const url = normalizeWebsiteUrl(selectedUrlDraft.value)
  if (!url) {
    selectedUrlError.value = 'Enter a full https:// address'
    return
  }
  selectedUrlError.value = null
  selectedUrlDraft.value = url
  el.webUrl = url
  el.url = url
  el.filename = websiteLabel(url)
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

/** One button in the narrow-screen toolbar: icon over label, a comfortable tap target. */
const TOOL =
  'flex min-w-[4.5rem] shrink-0 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[12px] text-ink ' +
  'transition-colors duration-150 active:bg-surface disabled:opacity-35'

function apply() {
  emit('apply', elements.value, background.value)
}
</script>

<template>
  <!-- overscroll-none: a gesture that reaches the end of anything in here stops there, rather than
       carrying on into the page behind the editor. -->
  <div class="flex h-full flex-col overscroll-none">
    <div class="flex shrink-0 items-center justify-between gap-3 border-b border-line px-3 py-2.5 sm:px-6 sm:py-3">
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

    <div class="relative flex min-h-0 flex-1">
      <!-- Left rail: the source you are adding from, with its panel beside it. Desktop only; on a
           narrow screen the sources are in the bottom toolbar. -->
      <nav class="hidden w-20 shrink-0 flex-col items-center gap-1 border-r border-line py-3 lg:flex">
        <button
          v-for="p in PANELS"
          :key="p.id"
          type="button"
          class="flex w-16 flex-col items-center gap-1 rounded-xl px-2 py-2.5 text-[12px]
                 transition-colors duration-150"
          :class="panel === p.id
            ? 'bg-ink text-ink-inverse'
            : 'text-ink-muted hover:bg-surface hover:text-ink'"
          :aria-pressed="panel === p.id"
          @click="panel = p.id"
        >
          <component :is="p.icon" class="size-5" />
          {{ p.label }}
        </button>
      </nav>

      <aside
        v-show="isWide || sheet === 'sources'"
        class="flex flex-col overflow-y-auto transition-colors duration-200"
        :class="[
          isWide
            ? 'w-64 shrink-0 border-r p-3'
            : 'fixed inset-x-0 bottom-0 z-50 max-h-[60dvh] touch-pan-y overscroll-contain rounded-t-2xl border-t bg-canvas px-4 pt-2 pb-[calc(1rem_+_env(safe-area-inset-bottom))]',
          isPanelDragOver ? 'border-ink bg-surface' : 'border-line',
        ]"
        @dragenter.prevent="onPanelDragEnter"
        @dragover.prevent
        @dragleave.prevent="onPanelDragLeave"
        @drop.prevent="onPanelDrop"
      >
        <div v-if="!isWide" class="sticky -top-2 z-10 -mx-4 mb-2 flex items-center justify-between bg-canvas px-4 pt-2 pb-1">
          <span class="mx-auto mb-1 h-1 w-10 rounded-full bg-line-strong" aria-hidden="true" />
        </div>
        <div v-if="!isWide" class="mb-3 flex items-center justify-between">
          <p class="text-base text-ink">{{ panel === 'media' ? 'Media' : 'Website' }}</p>
          <button type="button" class="rounded-full p-1.5 text-ink-muted hover:bg-surface" aria-label="Close" @click="closeSheet">
            <IconClose class="size-5" />
          </button>
        </div>
        <template v-if="panel === 'media'">
          <button
            type="button"
            class="mb-2 flex items-center justify-center gap-1.5 rounded-lg border border-dashed
                   border-line-strong px-2 py-2 text-[12px] text-ink-muted transition-colors
                   duration-200 hover:border-ink hover:text-ink"
            @click="mediaInput?.click()"
          >
            <IconAddPhotoAlternateOutline class="size-4" />
            Upload, or drop files here
          </button>
          <input
            ref="mediaInput" type="file" accept="image/*,video/*" multiple class="hidden"
            @change="onMediaFiles"
          />

          <!-- On the canvas the moment it finishes, so the progress row is the only wait. -->
          <div v-if="uploadJobs.length" class="mb-2 flex flex-col gap-1.5">
            <div v-for="job in uploadJobs" :key="job.id" class="rounded-lg bg-surface p-2">
              <UploadStatus :job="job" done-label="Added to scene" />
            </div>
          </div>

          <input
            v-model="mediaQuery"
            type="search"
            placeholder="Search media"
            aria-label="Search media"
            class="mb-3 w-full rounded-lg border border-line-strong bg-canvas px-2.5 py-1.5 text-[13px]
                   text-ink focus:border-ink focus:outline-none"
          />
          <p v-if="!library.length && !uploadJobs.length" class="px-1 text-[13px] text-ink-muted">
            Nothing in your library yet. Upload above and it drops straight onto the canvas.
          </p>
          <p v-else-if="!filteredLibrary.length" class="px-1 text-[13px] text-ink-muted">
            Nothing matches that.
          </p>
          <ul v-else class="flex flex-col gap-1">
            <li v-for="m in filteredLibrary" :key="m.id">
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
        </template>

        <form v-else class="flex flex-col gap-2" @submit.prevent="addWebsite">
          <input
            v-model="websiteInput"
            type="text"
            inputmode="url"
            placeholder="example.com"
            aria-label="Website address"
            class="w-full rounded-lg border border-line-strong bg-canvas px-2.5 py-1.5 text-[13px]
                   text-ink focus:border-ink focus:outline-none"
          />
          <AppButton variant="secondary" size="sm" type="submit" block>
            <IconLanguage class="size-4" />
            Add website
          </AppButton>
          <p v-if="websiteError" class="text-[12px] text-danger">{{ websiteError }}</p>
          <p class="text-[12px] text-ink-subtle">Shown live. https only.</p>
        </form>
      </aside>

      <!-- Canvas -->
      <div
        ref="stageRef"
        class="flex min-w-0 flex-1 touch-none items-center justify-center overflow-hidden bg-surface p-4 select-none
               lg:touch-auto lg:overflow-auto lg:p-6"
        :class="!isWide && 'pb-4'"
        @click.self="select(null)"
      >
        <div class="flex justify-center" :style="frameOuterStyle" @click.self="select(null)">
          <div
            ref="canvasRef"
            class="relative w-full bg-black"
            :style="frameStyle"
            @click.self="select(null)"
            @dragover.prevent
            @drop.prevent="onCanvasDrop"
          >
            <!-- What the screen shows, clipped to the frame: an element hanging off the canvas
                 is cut off here exactly as the device will cut it off. `pointer-events-none` so
                 a click on bare canvas still reaches the frame below and deselects. -->
            <div class="pointer-events-none absolute inset-0 overflow-hidden">
              <div v-if="blurUrl" class="absolute inset-0 overflow-hidden" style="container-type: size">
                <img :src="blurUrl" alt="" class="select-none" :style="BLUR_IMAGE_STYLE" draggable="false" />
              </div>
              <div
                v-for="el in elements"
                :key="el.key"
                class="absolute"
                :style="{
                  left: `${el.x * 100}%`, top: `${el.y * 100}%`,
                  width: `${el.width * 100}%`, height: `${el.height * 100}%`,
                  zIndex: el.zIndex,
                }"
              >
                <div class="relative size-full overflow-hidden">
                  <!-- The page inside is not browsed here; the element is dragged. -->
                  <iframe
                    v-if="el.kind === 'web'"
                    :src="el.url"
                    title=""
                    class="pointer-events-none absolute left-0 top-0 origin-top-left border-0 bg-white"
                    :style="webFrameStyle(el)"
                    referrerpolicy="no-referrer"
                    sandbox="allow-scripts allow-same-origin"
                  />
                  <template v-else-if="el.mediaWidth && el.mediaHeight">
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
              </div>
            </div>

            <!-- Selection, deliberately NOT clipped: an element dragged half off the canvas keeps
                 its outline and handles reachable out in the margin, the way every design tool
                 behaves. The layer itself ignores pointer events; only the boxes take them, so
                 clicking bare canvas still deselects. -->
            <div class="pointer-events-none absolute inset-0">
              <div
                v-for="el in elements"
                :key="el.key"
                class="pointer-events-auto absolute touch-none select-none"
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
                <div
                  v-for="corner in CORNERS"
                  v-show="selectedKey === el.key && !cropMode"
                  :key="corner"
                  title="Resize"
                  class="absolute size-3 -translate-x-1/2 -translate-y-1/2 touch-none rounded-full border-2 border-ink bg-canvas
                         before:absolute before:-inset-3 before:content-[''] lg:before:-inset-1.5"
                  :style="{ left: HANDLE_POS[corner].left, top: HANDLE_POS[corner].top, cursor: HANDLE_CURSOR[corner] }"
                  @pointerdown.stop="onHandlePointerDown(corner, $event)"
                  @pointermove.stop="onHandlePointerMove"
                  @pointerup.stop="onHandlePointerUp"
                  @pointercancel.stop="onHandlePointerUp"
                />

                <!-- Side handles: bars at each side's midpoint, Canva's crop tell — drag one
                     inward to crop that side, back out to reveal it again. Shown whenever the
                     element is selected; a website's resize that side instead. -->
                <div
                  v-for="edge in EDGES"
                  v-show="selectedKey === el.key"
                  :key="edge"
                  :title="el.kind === 'web' ? 'Resize' : 'Crop'"
                  class="absolute -translate-x-1/2 -translate-y-1/2 touch-none rounded-full border-2 border-ink bg-canvas
                         before:absolute before:-inset-3 before:content-[''] lg:before:-inset-1.5"
                  :class="edge === 'n' || edge === 's' ? 'h-1.5 w-8' : 'h-8 w-1.5'"
                  :style="{ left: EDGE_POS[edge].left, top: EDGE_POS[edge].top, cursor: EDGE_CURSOR[edge] }"
                  @pointerdown.stop="onEdgeHandlePointerDown(edge, $event)"
                  @pointermove.stop="onEdgeHandlePointerMove"
                  @pointerup.stop="onEdgeHandlePointerUp"
                  @pointercancel.stop="onEdgeHandlePointerUp"
                />
              </div>

              <template v-if="selected && floating && !floatingHidden">
                <div
                  class="pointer-events-auto absolute z-[1000] flex items-center gap-0.5 rounded-full bg-canvas p-1 ring-1 ring-line"
                  :style="floating.pill"
                  @pointerdown.stop
                  @click.stop
                >
                  <button
                    type="button"
                    class="flex size-9 items-center justify-center rounded-full text-ink transition-colors duration-150
                           hover:bg-surface hover:text-danger focus-visible:outline-2 focus-visible:outline-brand-bright"
                    title="Delete"
                    aria-label="Delete element"
                    @click="deleteSelected"
                  >
                    <IconDeleteOutline class="size-5" />
                  </button>
                </div>
                <button
                  v-if="selected.kind !== 'web'"
                  type="button"
                  class="pointer-events-auto absolute z-[1000] flex size-9 items-center justify-center rounded-full bg-canvas
                         text-ink ring-1 ring-line transition-colors duration-150 hover:bg-surface
                         focus-visible:outline-2 focus-visible:outline-brand-bright"
                  :style="floating.rotate"
                  title="Rotate"
                  aria-label="Rotate a quarter turn"
                  @pointerdown.stop
                  @click.stop="rotateSelected"
                >
                  <IconRotateRight class="size-5" />
                </button>
              </template>
            </div>

            <div
              v-if="!elements.length"
              class="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center text-[13px] text-white/40"
            >
              <span class="hidden lg:inline">Drag media from the left, or click it, to start this scene</span>
              <span class="lg:hidden">Tap Media below to start this scene</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right panel: layers on top, details for whatever's selected below -->
      <aside
        v-show="isWide || sheet === 'edit'"
        class="flex flex-col overflow-y-auto border-line"
        :class="isWide
          ? 'w-72 shrink-0 border-l'
          : 'fixed inset-x-0 bottom-0 z-50 max-h-[60dvh] touch-pan-y overscroll-contain rounded-t-2xl border-t bg-canvas pb-[env(safe-area-inset-bottom)]'"
      >
        <div v-if="!isWide" class="flex items-center justify-between px-4 pt-3">
          <p class="text-base text-ink">{{ selected ? 'Edit' : 'Scene' }}</p>
          <button type="button" class="rounded-full p-1.5 text-ink-muted hover:bg-surface" aria-label="Close" @click="closeSheet">
            <IconClose class="size-5" />
          </button>
        </div>
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

            <form v-if="selected.kind === 'web'" class="flex flex-col gap-2" @submit.prevent="onSelectedUrlCommit">
              <p class="text-[13px] text-ink-subtle">Address</p>
              <input
                v-model="selectedUrlDraft"
                type="text"
                inputmode="url"
                aria-label="Website address"
                class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
                       focus:border-ink focus:outline-none"
                @blur="onSelectedUrlCommit"
              />
              <p v-if="selectedUrlError" class="text-[12px] text-danger">{{ selectedUrlError }}</p>
            </form>

            <div v-else class="flex flex-col gap-2">
              <p class="text-[13px] text-ink-subtle">Size</p>
              <div class="flex gap-2" role="radiogroup" aria-label="Size">
                <AppButton
                  :variant="selected.fit === 'contain' ? 'primary' : 'secondary'" size="sm"
                  role="radio" :aria-checked="selected.fit === 'contain'"
                  @click="setFit('contain')"
                >
                  Fit
                </AppButton>
                <AppButton
                  :variant="selected.fit === 'cover' ? 'primary' : 'secondary'" size="sm"
                  role="radio" :aria-checked="selected.fit === 'cover'"
                  @click="setFit('cover')"
                >
                  Fill
                </AppButton>
              </div>
              <p class="text-[12px] text-ink-subtle">
                {{ selected.fit === 'cover' ? 'Covers its box; crop to choose what shows.' : 'Shows all of it; the scene background fills the rest.' }}
              </p>
            </div>

            <div v-if="selected.kind !== 'web'" class="flex flex-col gap-2">
              <p class="text-[13px] text-ink-subtle">Transform</p>
              <div class="flex flex-wrap gap-2">
                <AppButton variant="secondary" size="sm" @click="rotateSelected">
                  <IconRotateRight class="size-4" />
                  Rotate
                </AppButton>
                <AppButton
                  :variant="cropMode ? 'primary' : 'secondary'" size="sm"
                  :disabled="!selected.mediaWidth || selected.fit !== 'cover'"
                  :title="selected.fit !== 'cover' ? 'Crop applies to Fill' : undefined"
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
          <template v-else>
            <p class="text-[13px] text-ink-subtle">Select an item on the canvas to edit it.</p>
            <div class="flex flex-col gap-2">
              <p class="text-[13px] text-ink-subtle">Background</p>
              <div class="flex gap-2" role="radiogroup" aria-label="Background">
                <AppButton
                  v-for="option in SCENE_BACKGROUNDS"
                  :key="option.value"
                  :variant="background === option.value ? 'primary' : 'secondary'"
                  size="sm"
                  role="radio"
                  :aria-checked="background === option.value"
                  @click="background = option.value"
                >
                  {{ option.label }}
                </AppButton>
              </div>
              <p class="text-[12px] text-ink-subtle">
                Fills any part of the screen the scene doesn't cover.
                <template v-if="background === 'blur'">
                  Uses a blurred copy of the largest picture or video (a video's thumbnail).
                </template>
              </p>
            </div>
          </template>
        </div>
      </aside>

      <!-- Behind an open sheet: tapping outside it closes it. -->
      <div v-if="!isWide && sheet" class="fixed inset-0 z-40 touch-none bg-ink/30" aria-hidden="true" @click="closeSheet" />
    </div>

    <!-- Crop on a narrow screen: the zoom slider sits just above the toolbar, so the canvas stays
         in view while you pan and zoom. -->
    <div
      v-if="!isWide && selected && cropMode"
      class="flex shrink-0 items-center gap-3 border-t border-line bg-canvas px-4 py-2"
    >
      <span class="text-[12px] text-ink-muted">Zoom</span>
      <input
        type="range" min="1" max="3" step="0.05"
        :value="selected.cropZoom ?? 1"
        aria-label="Crop zoom"
        class="h-1.5 flex-1 cursor-pointer accent-brand"
        @input="onZoomInput"
      />
      <button type="button" class="text-[12px] text-ink-muted" @click="resetCrop">Reset</button>
    </div>

    <!-- The bottom toolbar (below lg), like Canva's: sources when nothing is selected, and what can
         be done to the selection when something is. Scrolls sideways when the tools outgrow it. -->
    <nav
      v-if="!isWide"
      class="flex shrink-0 touch-pan-x gap-1 overflow-x-auto overscroll-contain border-t border-line bg-canvas px-2 pt-1.5 pb-[calc(0.375rem_+_env(safe-area-inset-bottom))]"
      aria-label="Scene tools"
    >
      <template v-if="!selected">
        <button type="button" :class="TOOL" @click="openSources('media')">
          <IconPhotoLibraryOutline class="size-6" aria-hidden="true" />Media
        </button>
        <button type="button" :class="TOOL" @click="openSources('website')">
          <IconLanguage class="size-6" aria-hidden="true" />Website
        </button>
        <button v-if="elements.length" type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconLayersOutline class="size-6" aria-hidden="true" />Layers
        </button>
        <button type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconWallpaper class="size-6" aria-hidden="true" />Background
        </button>
      </template>
      <template v-else>
        <template v-if="selected.kind !== 'web'">
          <button
            type="button" :class="TOOL"
            :aria-pressed="selected.fit === 'cover'"
            @click="setFit(selected.fit === 'cover' ? 'contain' : 'cover')"
          >
            <IconAspectRatio class="size-6" aria-hidden="true" />{{ selected.fit === 'cover' ? 'Fill' : 'Fit' }}
          </button>
          <button
            type="button" :class="[TOOL, cropMode && '!text-brand']"
            :aria-pressed="cropMode"
            :disabled="!selected.mediaWidth || selected.fit !== 'cover'"
            @click="cropMode = !cropMode"
          >
            <IconCrop class="size-6" aria-hidden="true" />Crop
          </button>
          <button
            v-if="selected.kind === 'video'"
            type="button" :class="TOOL"
            @click="selected.hasAudio = !selected.hasAudio"
          >
            <component :is="selected.hasAudio ? IconVolumeUp : IconVolumeOff" class="size-6" aria-hidden="true" />
            {{ selected.hasAudio ? 'Sound on' : 'Muted' }}
          </button>
        </template>
        <button v-else type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconLanguage class="size-6" aria-hidden="true" />Address
        </button>
        <button type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconLayersOutline class="size-6" aria-hidden="true" />Layers
        </button>
        <button type="button" :class="[TOOL, '!text-brand']" @click="select(null)">
          <IconCheck class="size-6" aria-hidden="true" />Done
        </button>
      </template>
    </nav>
  </div>
</template>
