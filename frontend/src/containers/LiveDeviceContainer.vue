<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconStop from '~icons/material-symbols/stop-circle-outline'

import { useFormat } from '@/hooks/useFormat'
import { useLiveControl } from '@/hooks/useLiveControl'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import { isPortrait } from '@/utils/orientation'

/**
 * Live Control for one screen: every scene of its playlist as a big tile, drawn exactly as the
 * screen draws it. Tap a tile and the screen shows that scene and holds it; tap another and it
 * moves; end live control and the playlist carries on. Built to be read from across a room —
 * this is the page open on a laptop while someone shows a customer the wall.
 */
const route = useRoute()
const router = useRouter()
const id = String(route.params.id)
const {
  device, resolution, playlist, scenes, liveSlotId, liveScene,
  isLoading, error, actionError, pendingSlotId, isEnding, hold, end,
} = useLiveControl(id)
const { duration, relativeTime } = useFormat()

/** The screen's own size, turned the way it is mounted, so tiles have its exact shape — a
 *  tablet reports its landscape panel even when it stands on end. A generic size until it has
 *  reported. Same rule as useScreenPresets. */
const screen = computed(() => {
  const d = device.value
  const portrait = !!d && isPortrait(d.orientation)
  const long = d?.screen_width && d?.screen_height ? Math.max(d.screen_width, d.screen_height) : 1920
  const short = d?.screen_width && d?.screen_height ? Math.min(d.screen_width, d.screen_height) : 1080
  return portrait ? { width: short, height: long } : { width: long, height: short }
})

/** Green means the screen will follow within seconds; anything else deserves a warning. */
const isOnline = computed(() => {
  const at = device.value?.last_seen_at
  return !!at && Date.now() - new Date(at).getTime() < 2 * 60_000
})

/** Portrait tiles are tall, so fewer fit a row; landscape tiles get three across on a wide
 *  window. Either way each one is big enough to point at from across a room. */
const gridClass = computed(() =>
  screen.value.height > screen.value.width ? 'grid-cols-2 lg:grid-cols-3 xl:grid-cols-4' : 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3',
)
const tileHeight = computed(() => (screen.value.height > screen.value.width ? 360 : 260))
</script>

<template>
  <div class="flex flex-col gap-6">
    <router-link
      :to="{ name: 'live' }"
      class="flex w-fit items-center gap-1 text-[13px] text-ink-muted transition-colors hover:text-ink"
    >
      <IconArrowBack class="size-4" aria-hidden="true" />
      Live Control
    </router-link>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading && !device" class="text-sm text-ink-muted">Loading…</p>

    <template v-else-if="device">
      <PageTitle :title="device.name || 'Unnamed screen'">
        <template #actions>
          <AppButton
            v-if="liveSlotId"
            variant="danger"
            :loading="isEnding"
            @click="end"
          >
            <IconStop class="size-5" aria-hidden="true" />
            End live control
          </AppButton>
        </template>
      </PageTitle>

      <!-- One line that says what state the screen is in, big enough to read at a glance. -->
      <div
        class="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl px-5 py-4"
        :class="liveSlotId ? 'bg-brand text-ink-inverse' : 'bg-canvas text-ink'"
      >
        <span
          v-if="liveSlotId"
          class="flex items-center gap-2 text-[11px] font-medium tracking-wider uppercase"
        >
          <span class="size-2 animate-pulse rounded-full bg-ink-inverse" aria-hidden="true" />
          Live
        </span>
        <p class="text-base">
          <template v-if="liveScene">
            Holding <b>scene {{ liveScene.number }}</b> · {{ liveScene.label }}
          </template>
          <template v-else-if="liveSlotId">Holding a scene that is no longer in this playlist</template>
          <template v-else-if="playlist">
            Playing <b>{{ playlist.name }}</b>
            <span v-if="resolution?.schedule_name" class="opacity-70"> via {{ resolution.schedule_name }}</span>
            — tap a scene to put it on the screen
          </template>
          <template v-else>No playlist assigned</template>
        </p>
        <span class="ml-auto flex items-center gap-2 text-[13px]" :class="liveSlotId ? 'opacity-80' : 'text-ink-muted'">
          <StatusDot :last-seen-at="device.last_seen_at" :show-label="false" />
          {{ isOnline ? 'Online' : `Last seen ${relativeTime(device.last_seen_at)}` }}
        </span>
      </div>

      <AppAlert v-if="!isOnline" tone="danger">
        This screen hasn't checked in for a while. It will follow along once it reconnects.
      </AppAlert>
      <AppAlert v-if="actionError" tone="danger">{{ actionError }}</AppAlert>

      <EmptyState
        v-if="!playlist"
        title="Nothing to control"
        description="Assign a playlist to this screen first — then every scene in it shows here as a button."
      >
        <template #actions>
          <AppButton size="sm" @click="router.push({ name: 'deploy', query: { screen: id } })">Assign a playlist</AppButton>
        </template>
      </EmptyState>
      <EmptyState
        v-else-if="!scenes.length"
        title="This playlist has no scenes"
        description="Add a picture, a video or a website to it and it will show here."
      >
        <template #actions>
          <AppButton size="sm" @click="router.push({ name: 'playlist-detail', params: { id: playlist.id } })">Open playlist</AppButton>
        </template>
      </EmptyState>

      <div v-else class="grid gap-4" :class="gridClass">
        <button
          v-for="scene in scenes"
          :key="scene.id"
          type="button"
          class="group relative flex flex-col overflow-hidden rounded-2xl bg-canvas text-left transition-all duration-200
                 focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
          :class="[
            scene.id === liveSlotId ? 'ring-4 ring-brand ring-inset' : 'hover:bg-surface',
            pendingSlotId === scene.id && 'opacity-70',
          ]"
          :aria-pressed="scene.id === liveSlotId"
          :disabled="pendingSlotId !== null"
          @click="hold(scene.id)"
        >
          <ScreenPreview
            :screen-width="screen.width"
            :screen-height="screen.height"
            :elements="scene.elements"
            :background="scene.background"
            :background-color="scene.backgroundColor"
            :max-height="tileHeight"
            still
            class="w-full"
          />
          <div class="flex items-center gap-3 px-4 pb-4">
            <span
              class="flex size-9 shrink-0 items-center justify-center rounded-full text-base font-medium tabular-nums"
              :class="scene.id === liveSlotId ? 'bg-brand text-ink-inverse' : 'bg-raised text-ink'"
            >{{ scene.number }}</span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-base text-ink">{{ scene.label }}</span>
              <span class="block text-[13px] text-ink-muted">
                {{ scene.elements.length === 1 ? duration(scene.durationSeconds) : `${scene.elements.length} elements · ${duration(scene.durationSeconds)}` }}
              </span>
            </span>
            <span
              v-if="scene.id === liveSlotId"
              class="flex shrink-0 items-center gap-1.5 rounded-full bg-brand px-2.5 py-1 text-[11px] font-medium tracking-wider text-ink-inverse uppercase"
            >
              <span class="size-1.5 animate-pulse rounded-full bg-ink-inverse" aria-hidden="true" />
              On screen
            </span>
            <span
              v-else-if="pendingSlotId === scene.id"
              class="shrink-0 text-[13px] text-ink-muted"
            >Sending…</span>
          </div>
        </button>
      </div>

      <p v-if="playlist && scenes.length" class="text-[13px] text-ink-subtle">
        The playlist resumes when you end live control. A hold that is never ended stops on its own after 4 hours.
      </p>
    </template>
  </div>
</template>
