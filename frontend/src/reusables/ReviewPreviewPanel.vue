<script setup lang="ts">
/**
 * The screen preview a review shows beside a list of scenes: which of the change's screens to
 * see it on, Play/Pause, and the scene drawn at that screen's shape. The list beside it owns
 * *which* scene — it hands over the running preview (usePlaylistPreview) — so a playlist review
 * and a campaign review draw the screen the same way.
 *
 * Only the screens the change reaches are offered (utils/reviewScreens.ts), at the size and
 * orientation they had when it was sent — no presets, and no other screens: the question a
 * review asks is "what will *these* screens show", not what it would look like anywhere.
 */
import { computed, ref, watch } from 'vue'
import IconPause from '~icons/material-symbols/pause'
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconTv from '~icons/material-symbols/tv-outline'

import type { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import AppButton from '@/reusables/AppButton.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import type { PreviewScreen } from '@/utils/reviewScreens'

const props = defineProps<{
  preview: ReturnType<typeof usePlaylistPreview>
  screens: PreviewScreen[]
}>()

/** Something to draw on even when a review names no screen at all. */
const FALLBACK: PreviewScreen = { id: 'fallback', name: 'Full HD', width: 1920, height: 1080, reported: false }

const screenId = ref(props.screens[0]?.id ?? FALLBACK.id)
watch(() => props.screens, (list) => {
  if (!list.some((s) => s.id === screenId.value)) screenId.value = list[0]?.id ?? FALLBACK.id
})
const screen = computed(() => props.screens.find((s) => s.id === screenId.value) ?? props.screens[0] ?? FALLBACK)

function optionLabel(s: PreviewScreen): string {
  return s.reported ? `${s.name} · ${s.width}×${s.height}` : `${s.name} · ${s.width}×${s.height} (size not reported)`
}
</script>

<template>
  <div class="flex flex-col gap-3 rounded-xl bg-surface p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <select
        v-if="screens.length > 1"
        v-model="screenId"
        class="max-w-full min-w-0 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
               focus:border-ink focus:outline-none"
        aria-label="Preview on screen"
      >
        <option v-for="s in screens" :key="s.id" :value="s.id">{{ optionLabel(s) }}</option>
      </select>
      <p v-else class="flex min-w-0 items-center gap-1.5 text-[13px] text-ink-muted">
        <IconTv class="size-4 shrink-0" aria-hidden="true" />
        <span class="truncate">{{ optionLabel(screen) }}</span>
      </p>
      <AppButton variant="secondary" size="sm" :disabled="!preview.enabled.value.length" @click="preview.toggle()">
        <component :is="preview.isPlaying.value ? IconPause : IconPlayArrow" class="size-4" aria-hidden="true" />
        {{ preview.isPlaying.value ? 'Pause' : 'Play' }}
      </AppButton>
    </div>
    <ScreenPreview
      :screen-width="screen.width"
      :screen-height="screen.height"
      :elements="preview.current.value?.elements ?? []"
      :background="preview.current.value?.background ?? 'black'"
      :background-color="preview.current.value?.backgroundColor ?? null"
    />
    <slot />
  </div>
</template>
