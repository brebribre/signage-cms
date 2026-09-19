<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import type { CSSProperties } from 'vue'

import {
  cropRectToStyle,
  effectiveDimensions,
  resolveCropRect,
  ROTATION_WRAPPER_STYLE,
  rotationStyle,
} from '@/utils/cropMath'
import type { DraftElement } from '@/hooks/usePlaylistEditor'
import type { SceneBackground } from '@/types/api'
import { BLUR_IMAGE_STYLE, blurImageUrl, blurSource, sceneBackdrop } from '@/utils/sceneBackground'
import { TEXT_DEFAULT_STYLE, textBoxStyle } from '@/utils/textStyle'
import { websiteLayoutScreen } from '@/utils/websiteLayout'

/**
 * A device screen, drawn at its real aspect ratio and scaled to fit the space it is given —
 * a scene of one or more positioned elements, not a single full-bleed media file.
 *
 * `fit` maps **exactly** onto CSS `object-fit`, which is what makes this preview trustworthy
 * rather than an approximation:
 *
 *   contain → object-fit: contain → Media3 RESIZE_MODE_FIT
 *   cover   → object-fit: cover   → Media3 RESIZE_MODE_ZOOM
 *   stretch → object-fit: fill    → Media3 RESIZE_MODE_FILL
 *
 * The screen is black because a signage panel is black behind whatever isn't covered by an
 * element — the whole point of an empty or partial scene is showing you exactly how much
 * black you are buying.
 */
const props = withDefaults(
  defineProps<{
    screenWidth: number
    screenHeight: number
    elements: DraftElement[]
    background?: SceneBackground
    backgroundColor?: string | null
    maxHeight?: number
  }>(),
  { maxHeight: 420, background: 'black' },
)

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
  background: sceneBackdrop(props.background, props.backgroundColor),
}))

const sortedElements = computed(() => [...props.elements].sort((a, b) => a.zIndex - b.zIndex))

/** The blurred picture behind the scene, when it has one — see utils/sceneBackground.ts. */
const blurUrl = computed(() => {
  if (props.background !== 'blur') return null
  const source = blurSource(props.elements)
  return source ? blurImageUrl(source) : null
})

/**
 * A website is laid out at the screen's real pixel size, then scaled down with the frame — so
 * the preview shows the desktop layout the screen will, not the phone layout a 300px-wide
 * iframe would get. The frame's rendered width is measured, since CSS can't divide lengths.
 */
const frameRef = ref<HTMLElement | null>(null)
const frameWidth = ref(0)
let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    frameWidth.value = frameRef.value?.clientWidth ?? 0
  })
  if (frameRef.value) resizeObserver.observe(frameRef.value)
})
onUnmounted(() => resizeObserver?.disconnect())

/**
 * Which files have arrived. Until one has, its element shows a placeholder, so a slow image
 * reads as "still loading" rather than as a scene with a hole in it. Kept by URL across scenes:
 * going back to a scene whose files are already here shows them straight away. A file that
 * fails counts as arrived too — a placeholder that never ends would be its own lie.
 */
const arrived = reactive(new Set<string>())
const markArrived = (url: string) => arrived.add(url)

function webStyle(el: DraftElement): CSSProperties {
  const layout = websiteLayoutScreen(props.screenWidth, props.screenHeight)
  return {
    width: `${layout.width * el.width}px`,
    height: `${layout.height * el.height}px`,
    transform: `scale(${frameWidth.value / layout.width})`,
    transformOrigin: 'top left',
  }
}

/** The frame's rendered height, for text sized as a fraction of the screen. */
const frameHeight = computed(() => frameWidth.value * (props.screenHeight / props.screenWidth))
function textStyle(el: DraftElement): CSSProperties {
  return textBoxStyle(el.textStyle ?? TEXT_DEFAULT_STYLE, frameHeight.value)
}

function boxStyle(el: DraftElement): CSSProperties {
  return {
    position: 'absolute',
    left: `${el.x * 100}%`,
    top: `${el.y * 100}%`,
    width: `${el.width * 100}%`,
    height: `${el.height * 100}%`,
    zIndex: el.zIndex,
    overflow: 'hidden',
  }
}

/** This element's own target aspect ratio — its box's fraction of the frame, corrected by
 *  the frame's real aspect ratio (a box that's 50% wide and 50% tall isn't square unless the
 *  frame itself is). */
function targetAspect(el: DraftElement): number {
  return (el.width / el.height) * (props.screenWidth / props.screenHeight)
}

/**
 * `cover`: the exact crop/rotate composition this session's crop and rotation work already
 * verified — resolveCropRect + cropRectToStyle position a wrapper sized for the element's
 * *effective* (post-rotation) aspect ratio, and the innermost media element is the only
 * thing that actually rotates, via `rotationStyle`'s container-query sizing.
 *
 * `contain`/`stretch`: the wrapper is the whole box, and the media inside is rotated the same
 * way, then letterboxed (`contain`, what media added to a playlist gets) or stretched by
 * `object-fit`. Its letterbox is transparent, so a blurred scene background shows through.
 */
function wrapperStyle(el: DraftElement): CSSProperties {
  if (!el.mediaWidth || !el.mediaHeight) return {}
  if (el.fit === 'cover') {
    const eff = effectiveDimensions(el.mediaWidth, el.mediaHeight, el.rotationDegrees)
    const rect = resolveCropRect(
      eff.width, eff.height, targetAspect(el),
      el.cropX ?? 0.5, el.cropY ?? 0.5, el.cropZoom ?? 1,
    )
    return { position: 'absolute', ...cropRectToStyle(rect), ...ROTATION_WRAPPER_STYLE } as CSSProperties
  }
  return { position: 'absolute', inset: 0, ...ROTATION_WRAPPER_STYLE } as CSSProperties
}

function mediaStyle(el: DraftElement): CSSProperties {
  if (el.fit === 'cover') return rotationStyle(el.rotationDegrees) as CSSProperties
  return { ...rotationStyle(el.rotationDegrees), objectFit: el.fit === 'stretch' ? 'fill' : 'contain' } as CSSProperties
}
</script>

<template>
  <!-- The bezel is an outline, not a border: an outline adds no size, so the screen area keeps
       its exact aspect ratio. The padding leaves room for it inside whatever holds the preview.
       Square corners, because the panels are square — a rounded preview would promise a shape
       the hardware does not have. -->
  <div class="flex flex-col items-center p-2.5">
    <div
      ref="frameRef"
      class="relative overflow-hidden bg-black outline-[10px] outline-solid outline-ink"
      :style="frameStyle"
    >
      <div v-if="blurUrl" class="absolute inset-0 overflow-hidden" style="container-type: size">
        <img :src="blurUrl" alt="" class="select-none" :style="BLUR_IMAGE_STYLE" />
      </div>
      <div v-for="el in sortedElements" :key="el.key" :style="boxStyle(el)">
        <!-- Not clickable, like the screen itself. -->
        <iframe
          v-if="el.kind === 'web'"
          :src="el.url"
          title=""
          class="pointer-events-none border-0 bg-white"
          :style="webStyle(el)"
          referrerpolicy="no-referrer"
          sandbox="allow-scripts allow-same-origin"
        />
        <div v-else-if="el.kind === 'text'" :style="textStyle(el)">{{ el.text }}</div>
        <div v-else :style="wrapperStyle(el)">
          <video
            v-if="el.kind === 'video'"
            :src="el.url"
            class="select-none"
            :style="mediaStyle(el)"
            :muted="!el.hasAudio"
            @loadeddata="markArrived(el.url)"
            @error="markArrived(el.url)"
            autoplay
            loop
            playsinline
          />
          <img
            v-else
            :src="el.url"
            alt=""
            class="select-none"
            :style="mediaStyle(el)"
            @load="markArrived(el.url)"
            @error="markArrived(el.url)"
          />
        </div>
        <Transition leave-active-class="transition-opacity duration-200" leave-to-class="opacity-0">
          <div
            v-if="el.kind !== 'web' && el.kind !== 'text' && !arrived.has(el.url)"
            class="preview-loading absolute inset-0 overflow-hidden bg-white/10"
            role="status"
            aria-label="Loading"
          />
        </Transition>
      </div>
      <div v-if="!elements.length" class="flex size-full items-center justify-center text-[13px] text-white/40">
        Nothing to preview
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The same sweep as SkeletonBlock, dimmed for a black screen. */
.preview-loading::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.12), transparent);
  animation: preview-sweep 1.4s ease-in-out infinite;
}
@keyframes preview-sweep {
  to {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .preview-loading::after {
    animation: none;
  }
}
</style>
