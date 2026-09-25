<script setup lang="ts">
import { ACCEPTED_MEDIA } from '@/utils/mediaTypes'
import { computed, onMounted, onUnmounted, ref, shallowReactive, watch } from 'vue'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconBolt from '~icons/material-symbols/bolt'
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
import IconLeftPanelClose from '~icons/material-symbols/left-panel-close-outline'
import IconRightPanelClose from '~icons/material-symbols/right-panel-close-outline'
import IconRightPanelOpen from '~icons/material-symbols/right-panel-open-outline'
import IconTextFields from '~icons/material-symbols/text-fields'
import IconFormatAlignLeft from '~icons/material-symbols/format-align-left'
import IconFormatAlignCenter from '~icons/material-symbols/format-align-center'
import IconFormatAlignRight from '~icons/material-symbols/format-align-right'
import IconFormatBold from '~icons/material-symbols/format-bold'
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
import {
  MAX_LIVE_ELEMENTS,
  isLiveKind,
  liveBlockReason,
  liveBudget,
  mediaToDraftElement,
  textToDraftElement,
  websiteToDraftElement,
} from '@/hooks/usePlaylistEditor'
import { TEXT_DEFAULT_STYLE, TEXT_PRESETS, textBoxStyle, textLabel } from '@/utils/textStyle'
import { websiteLayoutScreen } from '@/utils/websiteLayout'
import { normalizeWebsiteUrl, websiteLabel } from '@/utils/websiteUrl'
import type { DraftElement, DraftItem } from '@/hooks/usePlaylistEditor'
import type { MediaRead, SceneBackground } from '@/types/api'
import { BLUR_IMAGE_STYLE, DEFAULT_BACKGROUND_COLOR, SCENE_BACKGROUNDS, blurImageUrl, blurSource, sceneBackdrop } from '@/utils/sceneBackground'
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
  apply: [elements: DraftElement[], background: SceneBackground, backgroundColor: string | null]
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
  const blocked = liveBlockReason(budget.value, media.kind)
  if (blocked) showNotice(`${media.filename} is in your library, but not in this scene. ${blocked}`)
  else addFromMedia(media)
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
const backgroundColor = ref<string | null>(props.item.backgroundColor)
function pickBackground(value: SceneBackground) {
  background.value = value
  if (value === 'color' && !backgroundColor.value) backgroundColor.value = DEFAULT_BACKGROUND_COLOR
}

// --- The live budget: how many videos and websites this scene holds against what a screen can
// run at once (see usePlaylistEditor.ts). Shown in the header the whole time, so the limit is
// known before it is hit; when it is hit, the thing you tried says why instead of doing nothing.
const budget = computed(() => liveBudget(elements.value))
const LIVE_HINT =
  `Videos and websites play live on the screen and are heavy for it. ` +
  `A scene can have up to ${MAX_LIVE_ELEMENTS} of them, and only one video. Pictures don't count.`
const notice = ref<string | null>(null)
let noticeTimer: ReturnType<typeof setTimeout> | null = null
function showNotice(text: string) {
  notice.value = text
  if (noticeTimer) clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => { notice.value = null }, 5000)
}
onUnmounted(() => { if (noticeTimer) clearTimeout(noticeTimer) })
/** What stops Apply: a scene from before the limits, with more live elements than fit. */
const overMessage = computed(() => {
  if (!budget.value.over) return null
  const tooManyVideos = budget.value.videos > 1
  return tooManyVideos
    ? 'This scene has more than one video. Remove the extra video to apply.'
    : `This scene has ${budget.value.live} live elements; a screen can only run ${MAX_LIVE_ELEMENTS}. Remove one to apply.`
})
const blurUrl = computed(() => {
  if (background.value !== 'blur') return null
  const source = blurSource(elements.value)
  return source ? blurImageUrl(source) : null
})
const selectedKey = ref<string | null>(null)
const selected = computed(() => elements.value.find((e) => e.key === selectedKey.value) ?? null)

const KIND_ICON = { image: IconImageOutline, video: IconVideocam, web: IconLanguage, text: IconTextFields } as const

/** The left rail, Canva-style: pick a source, its panel opens beside it. Two for now; another
 *  source is one more entry here and one more branch in the panel below. */
const PANELS = [
  { id: 'media', label: 'Media', icon: IconPhotoLibraryOutline },
  { id: 'website', label: 'Website', icon: IconLanguage },
  { id: 'text', label: 'Text', icon: IconTextFields },
  { id: 'background', label: 'Background', icon: IconWallpaper },
] as const
type PanelId = (typeof PANELS)[number]['id']
const panel = ref<PanelId>('media')

// --- The two side panels fold away on a wide screen, for more room around the canvas. The left
// one like Canva's: the rail stays, and clicking the highlighted source closes its panel (any
// other source opens it). Remembered in this browser only; a blocked storage just means both
// start open. ---
function readOpen(key: string): boolean {
  try { return localStorage.getItem(key) !== '0' } catch { return true }
}
function writeOpen(key: string, open: boolean) {
  try { localStorage.setItem(key, open ? '1' : '0') } catch { /* private window: not remembered */ }
}
const leftOpen = ref(readOpen('sceneEditor.leftOpen'))
const rightOpen = ref(readOpen('sceneEditor.rightOpen'))
watch(leftOpen, (v) => writeOpen('sceneEditor.leftOpen', v))
watch(rightOpen, (v) => writeOpen('sceneEditor.rightOpen', v))

function pickPanel(id: PanelId) {
  if (panel.value === id) leftOpen.value = !leftOpen.value
  else {
    panel.value = id
    leftOpen.value = true
  }
}

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

// --- Floating controls on the canvas, Canva-style: one pill above the selected element with its
// actions side by side — Crop, Rotate, Delete, whichever apply. It goes below when there isn't
// room above, inside the element when there's room on neither side, and is held on the canvas
// horizontally. Hidden while the element is being dragged or resized, so it never gets in the
// way; kept while cropping, since its Crop button is how cropping ends. ---

const FLOAT_GAP = 12
/** Height a floating control needs, plus its gap — room required on a side before it goes there. */
const FLOAT_ROOM = 48
const floatingHidden = computed(() => dragging.value || !!resizingCorner.value || !!resizingEdge.value)

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

  // One pill, its buttons side by side: above the element, else below it, else just inside its
  // visible top when it fills the canvas.
  const pill: Place = roomAbove
    ? above(0)
    : roomBelow
      ? below(0)
      : { left: `${center}px`, top: `${Math.max(top, 0)}px`, transform: `translate(-50%, ${FLOAT_GAP}px)` }
  return { pill }
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
/** A picture being moved: its whole box and where the picture sits, at the start of the drag.
 *  Null for a website or text, which have nothing to crop and so stay on the canvas. */
let moveStart: { box: Box; media: MediaPlacement } | null = null
/** Set on press, turned into `moveStart` on the first real movement — so a plain click to
 *  select changes nothing about the element (not even a Fit picture into the Fill that looks
 *  the same, which is what reading its whole picture takes). */
let movePending = false
/** How much of a picture must stay on the canvas while it is moved off an edge, so it can
 *  always be grabbed again. */
const MIN_ON_CANVAS = 0.05

function elementTargetAspect(el: DraftElement): number {
  return (el.width / el.height) * canvasAspect.value
}

function currentCropRect(el: DraftElement, cx: number, cy: number) {
  const eff = effectiveDimensions(el.mediaWidth ?? 1, el.mediaHeight ?? 1, el.rotationDegrees)
  return resolveCropRect(eff.width, eff.height, elementTargetAspect(el), cx, cy, el.cropZoom ?? 1)
}

function onElementPointerDown(el: DraftElement, e: PointerEvent) {
  select(el.key)
  moveStart = null
  movePending = !cropMode.value
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
  const dx = (e.clientX - dragStartPointer.x) / box.width
  const dy = (e.clientY - dragStartPointer.y) / box.height
  if (!dx && !dy) return
  if (movePending) {
    movePending = false
    moveStart = fullOf(selected.value)
  }

  // A picture can be moved past the edges too, like scaling it past them: the whole picture moves,
  // the part outside is shown faded while dragging and cropped away on release, and within this
  // editing session dragging it back in brings that part back (see fullBoxes).
  if (moveStart) {
    const start = moveStart
    const x = Math.min(Math.max(start.box.x + dx, MIN_ON_CANVAS - start.box.width), 1 - MIN_ON_CANVAS)
    const y = Math.min(Math.max(start.box.y + dy, MIN_ON_CANVAS - start.box.height), 1 - MIN_ON_CANVAS)
    const full = { x, y, width: start.box.width, height: start.box.height }
    const media = { ...start.media, left: start.media.left + (x - start.box.x), top: start.media.top + (y - start.box.y) }
    showCut(selected.value, full, media)
    return
  }

  selected.value.x = dragStartBox.x + dx
  selected.value.y = dragStartBox.y + dy
  clampPosition(selected.value)
}

function onElementPointerUp(e: PointerEvent) {
  dragging.value = false
  dragElementRect = null
  moveStart = null
  movePending = false
  settleCut()
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

/**
 * Nothing leaves the canvas. A box stops at the edges rather than hanging off them, so what the
 * editor shows is exactly the box a screen gets — an element that ran past the edge was clipped
 * here but laid out from its real numbers on the device, and the two never quite agreed.
 *
 * Only the position is corrected here; a box that is itself larger than the canvas (made before
 * this rule) is pinned to the top-left and shrunk to fit by `normalizeToCanvas` on Apply.
 */
function clampPosition(el: { x: number; y: number; width: number; height: number }) {
  el.x = Math.min(Math.max(el.x, 0), Math.max(0, 1 - el.width))
  el.y = Math.min(Math.max(el.y, 0), Math.max(0, 1 - el.height))
}

const resizingCorner = ref<Corner | null>(null)
let resizeStartPointer = { x: 0, y: 0 }
let resizeStartBox = { x: 0, y: 0, width: 0, height: 0 }
/** Where the whole picture sits on the canvas when a corner drag starts, cropped parts included.
 *  Null for a website or text, which have no picture to crop. */
let resizeStartMedia: MediaPlacement | null = null

/**
 * While a picture is being scaled past the canvas edges: the whole enlarged box and where the
 * picture sits in it, so the editor can show what runs past the edge — faded, outside the
 * canvas — with the outline and handles on the full box, the way Canva shows an image hanging
 * off the page. Only for the length of the drag: on release the part outside is gone for good,
 * cropped away (see onHandlePointerMove), and only the canvas's contents are saved.
 */
const overflow = ref<{ key: string; box: Box; media: MediaPlacement } | null>(null)

type Box = { x: number; y: number; width: number; height: number }

/**
 * Within this editing session, the whole of each picture that was cut at a canvas edge: its full
 * box and where the picture sits — so dragging it back in, or scaling it from its real corners,
 * works on the whole picture, as in Canva. Each entry is only trusted while the element is still
 * exactly as that cut left it (`stamp`); any other edit — a side crop, a rotation, Fit — and the
 * element's own box is the whole of it again. Not saved: what is saved, and what a screen shows,
 * is only what is inside the canvas.
 */
const fullBoxes = shallowReactive(new Map<string, { box: Box; media: MediaPlacement; stamp: string }>())

function stampOf(el: DraftElement): string {
  return JSON.stringify([el.x, el.y, el.width, el.height, el.cropX, el.cropY, el.cropZoom, el.rotationDegrees, el.fit])
}

/** The remembered full box, if the element hasn't changed since it was cut. */
function rememberedFull(el: DraftElement) {
  const saved = fullBoxes.get(el.key)
  return saved && saved.stamp === stampOf(el) ? saved : null
}

/** The whole picture to move or scale: remembered from an earlier cut, or the element as it is.
 *  Null for a website or text. */
function fullOf(el: DraftElement): { box: Box; media: MediaPlacement } | null {
  const saved = rememberedFull(el)
  if (saved) return { box: { ...saved.box }, media: { ...saved.media } }
  const media = mediaPlacement(el)
  return media ? { box: { x: el.x, y: el.y, width: el.width, height: el.height }, media } : null
}

/** Shows the picture at its whole box `full`: the element becomes the part inside the canvas,
 *  cropped to match, and anything outside is kept for the faded preview. Does nothing past the
 *  tightest crop a scene can save — the picture simply stops there. */
function showCut(el: DraftElement, full: Box, media: MediaPlacement) {
  const left = Math.max(0, full.x)
  const top = Math.max(0, full.y)
  const right = Math.min(1, full.x + full.width)
  const bottom = Math.min(1, full.y + full.height)
  if (!setCropWindow(el, { x: left, y: top, width: right - left, height: bottom - top }, media)) return
  const past = full.x < 0 || full.y < 0 || full.x + full.width > 1 || full.y + full.height > 1
  overflow.value = past ? { key: el.key, box: full, media } : null
  if (!past) fullBoxes.delete(el.key)
}

/** On release: the faded part goes, and the whole picture is remembered for this session. */
function settleCut() {
  const o = overflow.value
  overflow.value = null
  if (!o) return
  const el = elements.value.find((e) => e.key === o.key)
  if (el) fullBoxes.set(o.key, { box: o.box, media: o.media, stamp: stampOf(el) })
}

/** Where an element's outline and handles go: its whole box while it runs past an edge — being
 *  dragged, or cut earlier in this session — and its own box otherwise. */
function displayBox(el: DraftElement): Box {
  if (overflow.value?.key === el.key) return overflow.value.box
  return rememberedFull(el)?.box ?? el
}

/** The faded picture outside the canvas: the enlarged box, and the picture placed in it exactly
 *  as the canvas places it (cropWrapperStyle's rule, relative to the full box). */
const overflowStyle = computed(() => {
  const o = overflow.value
  if (!o) return null
  return {
    box: {
      left: `${o.box.x * 100}%`, top: `${o.box.y * 100}%`,
      width: `${o.box.width * 100}%`, height: `${o.box.height * 100}%`,
    },
    media: {
      position: 'absolute' as const,
      left: `${((o.media.left - o.box.x) / o.box.width) * 100}%`,
      top: `${((o.media.top - o.box.y) / o.box.height) * 100}%`,
      width: `${(o.media.width / o.box.width) * 100}%`,
      height: `${(o.media.height / o.box.height) * 100}%`,
      ...ROTATION_WRAPPER_STYLE,
    },
  }
})
const overflowElement = computed(() => elements.value.find((e) => e.key === overflow.value?.key) ?? null)

function onHandlePointerDown(corner: Corner, e: PointerEvent) {
  if (!selected.value) return
  resizingCorner.value = corner
  resizeStartPointer = { x: e.clientX, y: e.clientY }
  // Read on the first movement, not here, so pressing a handle without dragging changes nothing.
  resizePending = true
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

let resizePending = false

function startResize(el: DraftElement) {
  const full = fullOf(el)
  resizeStartMedia = full?.media ?? null
  resizeStartBox = full ? { ...full.box } : { x: el.x, y: el.y, width: el.width, height: el.height }
}

/** Proportional scale about the opposite corner. Worked in a single scale factor — whichever
 *  axis the pointer has moved further along — so the box's aspect never drifts, and neither does
 *  the media's crop inside it (the same crop at the same aspect is the same picture, larger).
 *
 *  A picture can be scaled past the canvas edges, the way Canva lets an image run off the page —
 *  which is how one that isn't the screen's shape comes to cover it. Whatever goes past an edge
 *  is cropped away there and then: the box is cut at the edge and the crop is set so the part
 *  still inside looks exactly as it did. So the element is never stored hanging off the screen,
 *  nothing is shrunk or shifted to fit, and the screen shows exactly what the canvas shows.
 *
 *  A website or text has no picture to crop, so it still stops where the moving corner meets a
 *  canvas edge, keeping its shape. */
function onHandlePointerMove(e: PointerEvent) {
  if (!resizingCorner.value || !selected.value || !canvasRef.value) return
  const canvas = canvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - resizeStartPointer.x) / canvas.width
  const dy = (e.clientY - resizeStartPointer.y) / canvas.height
  if (!dx && !dy) return
  if (resizePending) {
    resizePending = false
    startResize(selected.value)
  }
  const corner = resizingCorner.value
  const sx = corner === 'ne' || corner === 'se' ? 1 : -1
  const sy = corner === 'sw' || corner === 'se' ? 1 : -1
  const start = resizeStartBox
  const wanted = Math.max(
    (start.width + sx * dx) / start.width,
    (start.height + sy * dy) / start.height,
  )
  const minScale = MIN_SIZE / Math.min(start.width, start.height)
  const anchorX = sx === 1 ? start.x : start.x + start.width
  const anchorY = sy === 1 ? start.y : start.y + start.height

  const m = resizeStartMedia
  if (m) {
    const scale = Math.max(minScale, wanted)
    // Scale the whole picture and its box about the anchored corner, then cut the box at the
    // canvas edges. The anchor is on the canvas, so something is always left.
    const about = (v: number, anchor: number) => anchor + (v - anchor) * scale
    const media = {
      left: about(m.left, anchorX), top: about(m.top, anchorY),
      width: m.width * scale, height: m.height * scale,
    }
    const full = {
      x: about(start.x, anchorX), y: about(start.y, anchorY),
      width: start.width * scale, height: start.height * scale,
    }
    showCut(selected.value, full, media)
    return
  }

  // How far the moving edges can travel from the anchored ones before touching the canvas edge.
  // Never below 1: a box already past the edge (from before the cap) may shrink but not grow.
  const roomX = sx === 1 ? 1 - anchorX : anchorX
  const roomY = sy === 1 ? 1 - anchorY : anchorY
  const maxScale = Math.max(1, Math.min(roomX / start.width, roomY / start.height))
  const scale = Math.max(minScale, Math.min(wanted, maxScale))
  const width = start.width * scale
  const height = start.height * scale
  selected.value.width = width
  selected.value.height = height
  selected.value.x = sx === 1 ? start.x : start.x + start.width - width
  selected.value.y = sy === 1 ? start.y : start.y + start.height - height
}

function onHandlePointerUp(e: PointerEvent) {
  resizingCorner.value = null
  resizeStartMedia = null
  resizePending = false
  settleCut()
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
type MediaPlacement = { left: number; top: number; width: number; height: number }
const EDGES: Edge[] = ['n', 's', 'e', 'w']

const resizingEdge = ref<Edge | null>(null)
let edgeStartPointer = { x: 0, y: 0 }
let edgeStartBox = { x: 0, y: 0, width: 0, height: 0 }
/** Where the whole media sits on the canvas (fractions), cropped parts included — held fixed for
 *  the length of a side-crop drag. Null for a website, which has nothing to crop. */
let edgeMedia: MediaPlacement | null = null

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

/** Where the whole picture sits on the canvas, cropped parts included, for an element that has
 *  one — after turning a Fit element into the Fill that looks the same, since cropping works on
 *  what is visible. Null for a website or text. */
function mediaPlacement(el: DraftElement): MediaPlacement | null {
  if (!el.mediaWidth || !el.mediaHeight) return null
  fillToVisibleMedia(el)
  const rect = currentCropRect(el, el.cropX ?? 0.5, el.cropY ?? 0.5)
  const width = el.width / rect.w
  const height = el.height / rect.h
  return { left: el.x - rect.x * width, top: el.y - rect.y * height, width, height }
}

/**
 * Show `box` of the picture that sits at `m`: the box becomes the element's, and the crop centre
 * and zoom are set to reproduce that window (resolveCropRect's inverse). False, with nothing
 * changed, when the window would be tighter than a scene can save.
 */
function setCropWindow(el: DraftElement, box: { x: number; y: number; width: number; height: number }, m: MediaPlacement): boolean {
  if (!el.mediaWidth || !el.mediaHeight || box.width <= 0 || box.height <= 0) return false
  // The visible window as a fraction of the media, and the zoom resolveCropRect needs to produce
  // a window that size at this box's aspect.
  const w = box.width / m.width
  const h = box.height / m.height
  const eff = effectiveDimensions(el.mediaWidth, el.mediaHeight, el.rotationDegrees)
  const mediaAspect = eff.width / eff.height
  const boxAspect = (box.width / box.height) * canvasAspect.value
  const fullWindowW = mediaAspect > boxAspect ? boxAspect / mediaAspect : 1
  const zoom = Math.max(1, fullWindowW / w)
  if (zoom > MAX_CROP_ZOOM) return false
  Object.assign(el, box)
  el.cropZoom = zoom
  el.cropX = (box.x - m.left) / m.width + w / 2
  el.cropY = (box.y - m.top) / m.height + h / 2
  return true
}

function onEdgeHandlePointerDown(edge: Edge, e: PointerEvent) {
  const el = selected.value
  if (!el) return
  edgeMedia = mediaPlacement(el)
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
  // A side can go back out as far as the media's own edge — and never past the canvas edge.
  const m = edgeMedia
  const minLeft = Math.max(0, m ? m.left : -Infinity)
  const maxRight = Math.min(1, m ? m.left + m.width : Infinity)
  const minTop = Math.max(0, m ? m.top : -Infinity)
  const maxBottom = Math.min(1, m ? m.top + m.height : Infinity)
  if (edge === 'e') right = Math.min(maxRight, Math.max(left + MIN_SIZE, right + dx))
  else if (edge === 'w') left = Math.max(minLeft, Math.min(right - MIN_SIZE, left + dx))
  else if (edge === 's') bottom = Math.min(maxBottom, Math.max(top + MIN_SIZE, bottom + dy))
  else top = Math.max(minTop, Math.min(bottom - MIN_SIZE, top + dy))

  const box = { x: left, y: top, width: right - left, height: bottom - top }
  if (!m || !el.mediaWidth || !el.mediaHeight) {
    Object.assign(el, box)
    return
  }
  // Cropped as far as a scene can be: the side stops.
  setCropWindow(el, box, m)
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
/** The whole box on the canvas: one that is larger than the canvas is shrunk to fit, keeping its
 *  shape, and then nudged in from any edge it crosses. For a scene made before boxes were capped
 *  at the edges, and for a rotation that turns a wide box into one taller than the screen. */
function normalizeToCanvas(el: { x: number; y: number; width: number; height: number }) {
  const shrink = Math.min(1, 1 / el.width, 1 / el.height)
  if (shrink < 1) {
    // Shrink about the centre, so a box that only just overflows barely moves.
    const cx = el.x + el.width / 2
    const cy = el.y + el.height / 2
    el.width *= shrink
    el.height *= shrink
    el.x = cx - el.width / 2
    el.y = cy - el.height / 2
  }
  clampPosition(el)
}

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
  // A wide box turned on a wide screen is now taller than the screen: keep it on the canvas.
  normalizeToCanvas(el)
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
  fullBoxes.delete(selectedKey.value)
  elements.value = elements.value.filter((e) => e.key !== selectedKey.value)
  selectedKey.value = null
  if (!isWide.value) closeSheet()
}

/** Backspace or Delete removes the selected element — never while typing somewhere (a text
 *  element's words, a website address), where those keys edit the text. */
function onDeleteKey(e: KeyboardEvent) {
  if (e.key !== 'Backspace' && e.key !== 'Delete') return
  if (e.metaKey || e.ctrlKey || e.altKey || !selectedKey.value) return
  const target = e.target as HTMLElement | null
  if (target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return
  e.preventDefault()
  deleteSelected()
}
onMounted(() => window.addEventListener('keydown', onDeleteKey))
onUnmounted(() => window.removeEventListener('keydown', onDeleteKey))

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
  const blocked = liveBlockReason(budget.value, m.kind)
  if (blocked) {
    showNotice(blocked)
    return
  }
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
  const blocked = liveBlockReason(budget.value, 'web')
  if (blocked) {
    showNotice(blocked)
    return
  }
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

// --- Text: added from the toolbar at one of three sizes, edited in the right panel. A text box
// starts wide and a few lines tall, centred; the words are the placeholder until typed over. ---

function addText(size: number) {
  const maxZ = Math.max(0, ...elements.value.map((e) => e.zIndex))
  const height = Math.min(0.5, size * 3)
  const el = textToDraftElement('Your text here', { size }, {
    x: 0.2, y: Math.max(0, 0.5 - height / 2), width: 0.6, height, zIndex: maxZ + 1,
  })
  elements.value.push(el)
  select(el.key)
  if (!isWide.value) closeSheet()
}

/** The canvas frame's rendered height — text is sized as a fraction of it. */
const canvasHeight = computed(() => canvasWidth.value / canvasAspect.value)
function textStyleFor(el: DraftElement) {
  return textBoxStyle(el.textStyle ?? TEXT_DEFAULT_STYLE, canvasHeight.value)
}
function onTextInput(el: DraftElement, event: Event) {
  el.text = (event.target as HTMLTextAreaElement).value
  el.filename = textLabel(el.text)
}
function setTextStyle(el: DraftElement, patch: Partial<NonNullable<DraftElement['textStyle']>>) {
  el.textStyle = { ...(el.textStyle ?? TEXT_DEFAULT_STYLE), ...patch }
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
  if (liveBlockReason(budget.value, m.kind)) {
    e.preventDefault()
    return
  }
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
  // Nothing leaves the editor hanging off the canvas — including elements placed before the cap.
  for (const el of elements.value) normalizeToCanvas(el)
  emit('apply', elements.value, background.value, backgroundColor.value)
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
      <div class="flex shrink-0 items-center gap-2 sm:gap-3">
        <span
          class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[12px] tabular-nums transition-colors duration-200"
          :class="budget.over
            ? 'border-danger/40 text-danger'
            : budget.liveFull ? 'border-line-strong text-ink' : 'border-line text-ink-muted'"
          :title="LIVE_HINT"
          :aria-label="`Live elements: ${budget.live} of ${MAX_LIVE_ELEMENTS}`"
        >
          <IconBolt class="size-3.5" aria-hidden="true" />
          Live {{ budget.live }}/{{ MAX_LIVE_ELEMENTS }}
        </span>
        <AppButton size="sm" :disabled="budget.over" @click="apply">
          <IconCheck class="size-4" />
          Apply
        </AppButton>
      </div>
    </div>
    <!-- One line under the header for the limit: what stopped the last add, or what stops Apply. -->
    <p
      v-if="overMessage || notice"
      class="shrink-0 border-b border-line px-3 py-1.5 text-[13px] sm:px-6"
      :class="overMessage ? 'bg-raised text-danger' : 'bg-raised text-ink-muted'"
      role="status"
    >
      {{ overMessage ?? notice }}
    </p>

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
          :class="panel === p.id && leftOpen
            ? 'bg-ink text-ink-inverse'
            : 'text-ink-muted hover:bg-surface hover:text-ink'"
          :aria-pressed="panel === p.id && leftOpen"
          :title="panel === p.id && leftOpen ? `Hide ${p.label}` : p.label"
          @click="pickPanel(p.id)"
        >
          <component :is="p.icon" class="size-5" />
          {{ p.label }}
        </button>
      </nav>

      <aside
        v-show="isWide ? leftOpen : sheet === 'sources'"
        class="relative flex flex-col overflow-y-auto transition-colors duration-200"
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
        <div v-if="isWide" class="-mt-1 mb-2 flex items-center justify-between">
          <p class="text-[13px] text-ink-subtle">{{ PANELS.find((p) => p.id === panel)?.label }}</p>
          <button
            type="button"
            class="flex size-7 items-center justify-center rounded-md text-ink-subtle hover:bg-surface hover:text-ink"
            title="Hide panel"
            aria-label="Hide panel"
            @click="leftOpen = false"
          >
            <IconLeftPanelClose class="size-4" />
          </button>
        </div>
        <div v-if="!isWide" class="sticky -top-2 z-10 -mx-4 mb-2 flex items-center justify-between bg-canvas px-4 pt-2 pb-1">
          <span class="mx-auto mb-1 h-1 w-10 rounded-full bg-line-strong" aria-hidden="true" />
        </div>
        <div v-if="!isWide" class="mb-3 flex items-center justify-between">
          <p class="text-base text-ink">{{ PANELS.find((p) => p.id === panel)?.label }}</p>
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
            ref="mediaInput" type="file" :accept="ACCEPTED_MEDIA" multiple class="hidden"
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
                :draggable="!liveBlockReason(budget, m.kind)"
                class="flex items-center gap-2.5 rounded-lg p-1.5 transition-colors duration-200"
                :class="liveBlockReason(budget, m.kind)
                  ? 'cursor-not-allowed opacity-40'
                  : 'cursor-grab hover:bg-surface active:cursor-grabbing'"
                :title="liveBlockReason(budget, m.kind) ?? 'Drag onto the canvas, or click to add'"
                :aria-disabled="!!liveBlockReason(budget, m.kind)"
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

        <div v-else-if="panel === 'text'" class="flex flex-col gap-2">
          <p class="px-1 text-[13px] text-ink-muted">Add a text box, then type over it.</p>
          <button
            v-for="preset in TEXT_PRESETS" :key="preset.label" type="button"
            class="rounded-lg bg-surface px-3 py-2.5 text-left text-ink transition-colors duration-150 hover:bg-raised"
            :style="{ fontSize: `${12 + preset.size * 100}px`, fontWeight: preset.size > 0.06 ? 700 : 400 }"
            @click="addText(preset.size)"
          >
            {{ preset.label }}
          </button>
        </div>

        <div v-else-if="panel === 'background'" class="flex flex-col gap-2">
          <p class="px-1 text-[13px] text-ink-muted">Fills any part of the screen the scene doesn't cover.</p>
          <div class="flex flex-col gap-1" role="radiogroup" aria-label="Background">
            <button
              v-for="option in SCENE_BACKGROUNDS" :key="option.value" type="button"
              role="radio" :aria-checked="background === option.value"
              class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors duration-150"
              :class="background === option.value ? 'bg-raised ring-2 ring-ink' : 'bg-surface hover:bg-raised'"
              @click="pickBackground(option.value)"
            >
              <span
                class="size-8 shrink-0 rounded-md border border-line-strong"
                :style="option.value === 'blur'
                  ? { background: blurUrl ? `url(${blurUrl}) center / cover` : 'linear-gradient(135deg, #7d8bd6, #1d2fa5)', filter: blurUrl ? 'blur(2px)' : undefined }
                  : { background: option.value === 'color' ? (backgroundColor ?? DEFAULT_BACKGROUND_COLOR) : '#000' }"
                aria-hidden="true"
              />
              <span class="min-w-0">
                <span class="block text-sm text-ink">{{ option.label }}</span>
                <span class="block text-[12px] text-ink-subtle">{{ option.hint }}</span>
              </span>
            </button>
          </div>
          <label v-if="background === 'color'" class="mt-1 flex items-center gap-2 px-1 text-[13px] text-ink-muted">
            <input
              type="color" :value="backgroundColor ?? DEFAULT_BACKGROUND_COLOR" aria-label="Background colour"
              class="size-8 cursor-pointer rounded border border-line-strong bg-canvas p-0.5"
              @input="backgroundColor = ($event.target as HTMLInputElement).value.toUpperCase()"
            />
            <span class="tabular-nums">{{ backgroundColor }}</span>
          </label>
        </div>

        <p v-else-if="liveBlockReason(budget, 'web')" class="rounded-lg bg-surface px-3 py-2 text-[13px] text-ink-muted">
          {{ liveBlockReason(budget, 'web') }}
        </p>
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
        :class="[!isWide && 'pb-4', overflow && 'lg:!overflow-hidden']"
        @click.self="select(null)"
      >
        <div class="flex justify-center" :style="frameOuterStyle" @click.self="select(null)">
          <div
            ref="canvasRef"
            class="relative w-full"
            :style="{ ...frameStyle, background: sceneBackdrop(background, backgroundColor) }"
            @click.self="select(null)"
            @dragover.prevent
            @drop.prevent="onCanvasDrop"
          >
            <!-- While a picture is scaled past the edges: all of it, faded. It sits under the
                 canvas contents, so inside the canvas the real picture covers it and only the part
                 past the edges shows. Gone on release, when that part is cropped away. -->
            <div
              v-if="overflowStyle && overflowElement"
              class="pointer-events-none absolute opacity-40"
              :style="overflowStyle.box"
              aria-hidden="true"
            >
              <div class="absolute inset-0 overflow-hidden">
                <div :style="overflowStyle.media">
                  <img
                    v-if="overflowElement.kind === 'image' || overflowElement.thumbnailUrl"
                    :src="overflowElement.kind === 'image' ? overflowElement.url : overflowElement.thumbnailUrl!"
                    alt=""
                    class="absolute max-w-none select-none"
                    :style="rotationStyle(overflowElement.rotationDegrees)"
                    draggable="false"
                  />
                </div>
              </div>
            </div>

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
                  <div v-else-if="el.kind === 'text'" :style="textStyleFor(el)">{{ el.text }}</div>
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
                  left: `${displayBox(el).x * 100}%`, top: `${displayBox(el).y * 100}%`,
                  width: `${displayBox(el).width * 100}%`, height: `${displayBox(el).height * 100}%`,
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
                  v-show="selectedKey === el.key && displayBox(el) === el"
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
                    v-if="selected.mediaWidth && selected.kind !== 'web' && selected.kind !== 'text'"
                    type="button"
                    class="flex size-9 items-center justify-center rounded-full transition-colors duration-150
                           focus-visible:outline-2 focus-visible:outline-brand-bright disabled:opacity-35"
                    :class="cropMode ? 'bg-ink text-ink-inverse' : 'text-ink hover:bg-surface'"
                    :disabled="selected.fit !== 'cover'"
                    :title="selected.fit !== 'cover' ? 'Crop applies to Fill' : cropMode ? 'Done cropping' : 'Crop'"
                    :aria-label="cropMode ? 'Done cropping' : 'Crop'"
                    :aria-pressed="cropMode"
                    @click="cropMode = !cropMode"
                  >
                    <IconCrop class="size-5" />
                  </button>
                  <button
                    v-if="selected.kind !== 'web'"
                    type="button"
                    class="flex size-9 items-center justify-center rounded-full text-ink transition-colors duration-150
                           hover:bg-surface focus-visible:outline-2 focus-visible:outline-brand-bright"
                    title="Rotate"
                    aria-label="Rotate a quarter turn"
                    @click="rotateSelected"
                  >
                    <IconRotateRight class="size-5" />
                  </button>
                  <button
                    type="button"
                    class="flex size-9 items-center justify-center rounded-full text-ink transition-colors duration-150
                           hover:bg-surface hover:text-danger focus-visible:outline-2 focus-visible:outline-brand-bright"
                    title="Delete (Backspace)"
                    aria-label="Delete element"
                    @click="deleteSelected"
                  >
                    <IconDeleteOutline class="size-5" />
                  </button>
                </div>
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
      <!-- Folded right panel: a thin strip to bring it back. -->
      <div v-if="isWide && !rightOpen" class="flex w-11 shrink-0 flex-col items-center border-l border-line py-3">
        <button
          type="button"
          class="flex size-8 items-center justify-center rounded-md text-ink-subtle hover:bg-surface hover:text-ink"
          title="Show panel"
          aria-label="Show layers and settings"
          @click="rightOpen = true"
        >
          <IconRightPanelOpen class="size-5" />
        </button>
      </div>
      <aside
        v-show="isWide ? rightOpen : sheet === 'edit'"
        class="relative flex flex-col overflow-y-auto border-line"
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
        <!-- Folds the panel away (wide screens). Top right, level with the Layers heading. -->
        <button
          v-if="isWide"
          type="button"
          class="absolute top-2.5 right-2.5 z-10 flex size-7 items-center justify-center rounded-md text-ink-subtle
                 hover:bg-surface hover:text-ink"
          title="Hide panel"
          aria-label="Hide panel"
          @click="rightOpen = false"
        >
          <IconRightPanelClose class="size-4" />
        </button>
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
            <span
              v-if="isLiveKind(el.kind)"
              class="shrink-0 rounded bg-surface px-1 text-[10px] uppercase tracking-wide text-ink-subtle"
              :title="LIVE_HINT"
            >live</span>
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

            <template v-else-if="selected.kind === 'text' && selected.textStyle">
              <label class="flex flex-col gap-1">
                <span class="text-[13px] text-ink-subtle">Text</span>
                <textarea
                  :value="selected.text ?? ''"
                  rows="4"
                  maxlength="2000"
                  aria-label="Text"
                  class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
                         focus:border-ink focus:outline-none"
                  @input="onTextInput(selected, $event)"
                />
              </label>
              <label class="flex flex-col gap-1">
                <span class="flex justify-between text-[13px] text-ink-subtle">
                  <span>Size</span><span class="tabular-nums">{{ Math.round(selected.textStyle.size * 100) }}% of the screen</span>
                </span>
                <input
                  type="range" min="2" max="30" step="1"
                  :value="Math.round(selected.textStyle.size * 100)"
                  class="accent-ink"
                  aria-label="Text size"
                  @input="setTextStyle(selected, { size: Number(($event.target as HTMLInputElement).value) / 100 })"
                />
              </label>
              <div class="flex flex-col gap-2">
                <p class="text-[13px] text-ink-subtle">Style</p>
                <div class="flex flex-wrap items-center gap-2">
                  <AppButton
                    :variant="selected.textStyle.weight === 'bold' ? 'primary' : 'secondary'" size="sm"
                    :aria-pressed="selected.textStyle.weight === 'bold'" title="Bold"
                    @click="setTextStyle(selected, { weight: selected.textStyle.weight === 'bold' ? 'regular' : 'bold' })"
                  >
                    <IconFormatBold class="size-4" />
                  </AppButton>
                  <div class="flex gap-1" role="radiogroup" aria-label="Alignment">
                    <AppButton
                      v-for="(icon, align) in { left: IconFormatAlignLeft, center: IconFormatAlignCenter, right: IconFormatAlignRight }"
                      :key="align"
                      :variant="selected.textStyle.align === align ? 'primary' : 'secondary'" size="sm"
                      role="radio" :aria-checked="selected.textStyle.align === align" :title="`Align ${align}`"
                      @click="setTextStyle(selected, { align })"
                    >
                      <component :is="icon" class="size-4" />
                    </AppButton>
                  </div>
                </div>
                <div class="flex flex-wrap items-center gap-3">
                  <label class="flex items-center gap-1.5 text-[13px] text-ink-muted">
                    <input
                      type="color" :value="selected.textStyle.color" aria-label="Text colour"
                      class="size-7 cursor-pointer rounded border border-line-strong bg-canvas p-0.5"
                      @input="setTextStyle(selected, { color: ($event.target as HTMLInputElement).value.toUpperCase() })"
                    />
                    Colour
                  </label>
                  <label class="flex items-center gap-1.5 text-[13px] text-ink-muted">
                    <input
                      type="checkbox" :checked="!!selected.textStyle.background" class="size-3.5 accent-ink"
                      aria-label="Background box"
                      @change="setTextStyle(selected, { background: ($event.target as HTMLInputElement).checked ? '#000000' : null })"
                    />
                    Box
                  </label>
                  <input
                    v-if="selected.textStyle.background"
                    type="color" :value="selected.textStyle.background" aria-label="Box colour"
                    class="size-7 cursor-pointer rounded border border-line-strong bg-canvas p-0.5"
                    @input="setTextStyle(selected, { background: ($event.target as HTMLInputElement).value.toUpperCase() })"
                  />
                </div>
              </div>
            </template>

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

            <!-- Crop, Rotate and Delete are on the element itself, in its floating pill. -->
            <div v-if="selected.kind === 'video'" class="flex flex-col gap-2">
              <p class="text-[13px] text-ink-subtle">Sound</p>
              <AppButton variant="secondary" size="sm" class="self-start" @click="selected.hasAudio = !selected.hasAudio">
                <component :is="selected.hasAudio ? IconVolumeUp : IconVolumeOff" class="size-4" />
                {{ selected.hasAudio ? 'Mute' : 'Unmute' }}
              </AppButton>
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
              <div class="flex gap-2">
                <AppButton variant="ghost" size="sm" @click="resetCrop">Reset crop</AppButton>
                <AppButton variant="secondary" size="sm" @click="cropMode = false">Done</AppButton>
              </div>
            </div>
          </template>
          <template v-else>
            <p class="text-[13px] text-ink-subtle">Select an item on the canvas to edit it. The background is under Background on the left.</p>
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
        <button type="button" :class="TOOL" @click="openSources('text')">
          <IconTextFields class="size-6" aria-hidden="true" />Text
        </button>
        <button v-if="elements.length" type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconLayersOutline class="size-6" aria-hidden="true" />Layers
        </button>
        <button type="button" :class="TOOL" @click="openSources('background')">
          <IconWallpaper class="size-6" aria-hidden="true" />Background
        </button>
      </template>
      <template v-else>
        <button v-if="selected.kind === 'text'" type="button" :class="TOOL" @click="sheet = 'edit'">
          <IconTextFields class="size-6" aria-hidden="true" />Edit text
        </button>
        <template v-else-if="selected.kind !== 'web'">
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
