<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'

import {
  cropRectToStyle,
  effectiveDimensions,
  resolveCropRect,
  ROTATION_WRAPPER_STYLE,
  rotationStyle,
} from '@/utils/cropMath'
import type { DraftElement } from '@/hooks/usePlaylistEditor'

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
    label?: string
    maxHeight?: number
  }>(),
  { maxHeight: 420 },
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
}))

const sortedElements = computed(() => [...props.elements].sort((a, b) => a.zIndex - b.zIndex))

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
 * `contain`/`stretch`: a simpler, approximate composition — plain `object-fit` plus a CSS
 * `rotate()` on the media element directly, with no effective-dimension swap. No element
 * produced by the current editor (SceneEditor.vue always writes `fit: 'cover'`) can combine
 * a non-cover fit with a non-zero rotation, so this path only exists for legacy data and
 * doesn't need the full treatment.
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
  return { position: 'absolute', inset: 0 }
}

function mediaStyle(el: DraftElement): CSSProperties {
  if (el.fit === 'cover') return rotationStyle(el.rotationDegrees) as CSSProperties
  const FIT_TO_CSS = { contain: 'contain', stretch: 'fill' } as const
  return {
    objectFit: FIT_TO_CSS[el.fit as 'contain' | 'stretch'],
    width: '100%',
    height: '100%',
    transform: el.rotationDegrees ? `rotate(${el.rotationDegrees}deg)` : undefined,
  }
}
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <div class="relative overflow-hidden rounded-md bg-black" :style="frameStyle">
      <div v-for="el in sortedElements" :key="el.key" :style="boxStyle(el)">
        <div :style="wrapperStyle(el)">
          <video
            v-if="el.kind === 'video'"
            :src="el.url"
            class="select-none"
            :style="mediaStyle(el)"
            :muted="!el.hasAudio"
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
          />
        </div>
      </div>
      <div v-if="!elements.length" class="flex size-full items-center justify-center text-[13px] text-white/40">
        Nothing to preview
      </div>
    </div>

    <p class="text-[13px] text-ink-subtle">{{ label }}</p>
  </div>
</template>
