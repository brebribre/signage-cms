<script setup lang="ts">
/**
 * The screen preview a review shows beside a list of scenes: a screen-size picker (your own
 * screens first, then presets), Play/Pause, and the scene drawn at that size. The list beside it
 * owns *which* scene — it hands over the running preview (usePlaylistPreview) — so a playlist
 * review and a campaign review draw the screen the same way.
 */
import { toRef } from 'vue'
import IconPause from '~icons/material-symbols/pause'
import IconPlayArrow from '~icons/material-symbols/play-arrow'

import type { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import { SCREEN_PRESETS, useScreenPresets } from '@/hooks/useScreenPresets'
import AppButton from '@/reusables/AppButton.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import type { DeviceRead } from '@/types/api'

const props = defineProps<{
  preview: ReturnType<typeof usePlaylistPreview>
  devices: DeviceRead[]
}>()

const { presetId, isCustom, customWidth, customHeight, screen, deviceOptions } = useScreenPresets(toRef(props, 'devices'))

const FIELD =
  'rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink focus:border-ink focus:outline-none'
</script>

<template>
  <div class="flex flex-col gap-3 rounded-xl bg-surface p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="presetId" :disabled="isCustom" :class="[FIELD, 'disabled:opacity-40']" aria-label="Screen size">
          <optgroup v-if="deviceOptions.length" label="Your screens">
            <option v-for="d in deviceOptions" :key="d.id" :value="d.id">{{ d.label }}</option>
          </optgroup>
          <optgroup label="Presets">
            <option v-for="p in SCREEN_PRESETS" :key="p.id" :value="p.id">{{ p.label }}</option>
          </optgroup>
        </select>
        <label class="flex items-center gap-1.5 text-[13px] text-ink-muted">
          <input v-model="isCustom" type="checkbox" class="size-3.5 accent-ink" />
          Custom
        </label>
        <template v-if="isCustom">
          <input v-model.number="customWidth" type="number" min="1" :class="[FIELD, 'w-20']" aria-label="Width" />
          <span class="text-[13px] text-ink-subtle">×</span>
          <input v-model.number="customHeight" type="number" min="1" :class="[FIELD, 'w-20']" aria-label="Height" />
        </template>
      </div>
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
