<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'

import { cropRectToStyle, resolveCropRect } from '@/utils/cropMath'

/**
 * A device screen, drawn at its real aspect ratio and scaled to fit the space it is given.
 *
 * The fit modes map **exactly** onto CSS `object-fit`, which is what makes this preview
 * trustworthy rather than an approximation:
 *
 *   contain → object-fit: contain → Media3 RESIZE_MODE_FIT
 *   cover   → object-fit: cover   → Media3 RESIZE_MODE_ZOOM
 *   stretch → object-fit: fill    → Media3 RESIZE_MODE_FILL
 *
 * The screen is black because a signage panel is black behind letterboxed content, and the
 * whole point of `contain` is to show you exactly how much black you are buying.
 */
const props = withDefaults(
  defineProps<{
    screenWidth: number
    screenHeight: number
    src: string | null
    kind: 'image' | 'video'
    fit: 'contain' | 'cover' | 'stretch'
    /** Intrinsic size of the media, for the upscaling warning and for resolving a crop. */
    mediaWidth?: number | null
    mediaHeight?: number | null
    label?: string
    maxHeight?: number
    /** Normalized crop center + zoom (see src/utils/cropMath.ts). Only applied when
     *  fit === 'cover' and cropZoom is set — otherwise rendering is untouched from before
     *  this prop existed, so every item that predates a crop keeps rendering exactly as is. */
    cropX?: number | null
    cropY?: number | null
    cropZoom?: number | null
    /** Video only. trimEndSeconds null means "to the end". */
    trimStartSeconds?: number
    trimEndSeconds?: number | null
    /** Video only. Every video is muted unless this is set. */
    hasAudio?: boolean
  }>(),
  { maxHeight: 420 },
)

const FIT_TO_CSS = { contain: 'contain', cover: 'cover', stretch: 'fill' } as const

const hasCrop = computed(() => props.fit === 'cover' && props.cropZoom != null)

const cropStyle = computed<CSSProperties>(() => {
  if (!hasCrop.value || !props.mediaWidth || !props.mediaHeight) return {}
  const rect = resolveCropRect(
    props.mediaWidth, props.mediaHeight, props.screenWidth / props.screenHeight,
    props.cropX ?? 0.5, props.cropY ?? 0.5, props.cropZoom ?? 1,
  )
  return { position: 'absolute', ...cropRectToStyle(rect) }
})

// Typed as CSSProperties rather than a bare string: Vue's `:style` binding will not accept
// `{ objectFit: string }`, only the narrowed literal union.
const mediaStyle = computed<CSSProperties>(() =>
  hasCrop.value ? cropStyle.value : { objectFit: FIT_TO_CSS[props.fit] },
)

// --- Video trim playback: without this, a saved trim would be invisible in the preview. ---

const videoRef = ref<HTMLVideoElement | null>(null)
const isTrimmed = computed(() => props.kind === 'video' && (props.trimStartSeconds || props.trimEndSeconds != null))

function onLoadedMetadata() {
  if (videoRef.value && props.trimStartSeconds) videoRef.value.currentTime = props.trimStartSeconds
}

function onTimeUpdate() {
  const v = videoRef.value
  if (!v || !isTrimmed.value) return
  const end = props.trimEndSeconds ?? v.duration
  if (v.currentTime >= end) v.currentTime = props.trimStartSeconds ?? 0
}

// A trim can change out from under an already-playing preview (e.g. reopening the editor and
// applying a new trim) — reseek rather than waiting for the next natural loop.
watch(() => [props.trimStartSeconds, props.trimEndSeconds, props.src], () => {
  if (videoRef.value && props.trimStartSeconds) videoRef.value.currentTime = props.trimStartSeconds
})

/**
 * Size by width, capped so the implied height never exceeds `maxHeight`.
 *
 * The obvious `width: 100% + max-height` is wrong: in a wide container the max-height clamps
 * the height while the width stays full, and the frame silently renders at the *container's*
 * aspect ratio rather than the screen's — a 16:9 panel drawn at 2.21:1, which is exactly the
 * lie a preview must not tell. Deriving the width from the height cap keeps the ratio exact
 * in both orientations.
 */
const frameStyle = computed(() => ({
  aspectRatio: `${props.screenWidth} / ${props.screenHeight}`,
  width: `min(100%, ${Math.round(props.maxHeight * (props.screenWidth / props.screenHeight))}px)`,
}))

/** True when the screen has more pixels than the file, so the panel upscales and softens. */
const isUpscaled = computed(() => {
  if (!props.mediaWidth || !props.mediaHeight) return false
  // Under `cover` the media is scaled to the larger ratio, under `contain` the smaller.
  const ratio =
    props.fit === 'cover'
      ? Math.max(props.screenWidth / props.mediaWidth, props.screenHeight / props.mediaHeight)
      : Math.min(props.screenWidth / props.mediaWidth, props.screenHeight / props.mediaHeight)
  return ratio > 1.15
})

/** How much of the media is cropped away under `cover`, as a percentage of its area. */
const cropPercent = computed(() => {
  if (props.fit !== 'cover' || !props.mediaWidth || !props.mediaHeight) return 0
  const screenAspect = props.screenWidth / props.screenHeight
  const mediaAspect = props.mediaWidth / props.mediaHeight
  const visible = mediaAspect > screenAspect ? screenAspect / mediaAspect : mediaAspect / screenAspect
  return Math.round((1 - visible) * 100)
})
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <div
      class="relative overflow-hidden rounded-md bg-black"
      :style="frameStyle"
    >
      <video
        v-if="src && kind === 'video'"
        ref="videoRef"
        :src="src"
        :class="hasCrop ? '' : 'size-full'"
        :style="mediaStyle"
        :muted="!hasAudio"
        autoplay
        :loop="!isTrimmed"
        playsinline
        @loadedmetadata="onLoadedMetadata"
        @timeupdate="onTimeUpdate"
      />
      <img
        v-else-if="src"
        :src="src"
        alt=""
        :class="hasCrop ? '' : 'size-full'"
        :style="mediaStyle"
      />
      <div v-else class="flex size-full items-center justify-center text-[13px] text-white/40">
        Nothing to preview
      </div>
    </div>

    <p class="text-[13px] text-ink-subtle">{{ label }}</p>

    <p v-if="cropPercent >= 5" class="text-center text-[13px] text-ink-muted">
      Fill crops about {{ cropPercent }}% of this image away.
    </p>
    <p v-if="isUpscaled" class="text-center text-[13px] text-danger">
      Lower resolution than the screen — this will look soft.
    </p>
  </div>
</template>
