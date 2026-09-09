<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { usePlaylistEditor } from '@/hooks/usePlaylistEditor'
import { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import { SCREEN_PRESETS, useScreenPresets } from '@/hooks/useScreenPresets'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DurationInput from '@/reusables/DurationInput.vue'
import MediaPlacementEditor from '@/reusables/MediaPlacementEditor.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import type { DraftItem } from '@/hooks/usePlaylistEditor'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)

const {
  playlist, draft, isLoading, isSaving, isDirty, error, saveError, deleteError,
  totalSeconds, enabledCount, addMedia, removeAt, move, save, setShuffle, remove,
} = usePlaylistEditor(id)
const { items: library, isLoading: libraryLoading } = useMedia()
const { items: devices } = useDevices()
const { duration } = useFormat()
const { presetId, isCustom, customWidth, customHeight, screen, deviceOptions } =
  useScreenPresets(devices)
const preview = usePlaylistPreview(() => draft.value)

const picking = ref(false)
const confirmingDelete = ref(false)
const picked = ref<Set<string>>(new Set())
const dragFrom = ref<number | null>(null)
const placing = ref<DraftItem | null>(null)

function togglePick(mediaId: string) {
  const next = new Set(picked.value)
  next.has(mediaId) ? next.delete(mediaId) : next.add(mediaId)
  picked.value = next
}

function confirmPick() {
  addMedia(library.value.filter((m) => picked.value.has(m.id)))
  picked.value = new Set()
  picking.value = false
}

function onDrop(to: number) {
  if (dragFrom.value !== null) move(dragFrom.value, to)
  dragFrom.value = null
}

async function onDelete() {
  if (await remove()) router.push({ name: 'playlists' })
  else confirmingDelete.value = false
}

function applyPlacement(patch: Partial<DraftItem>) {
  if (placing.value) Object.assign(placing.value, patch)
  placing.value = null
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'playlists' })">
      ← Playlists
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else-if="playlist">
      <PageTitle
        :title="playlist.name"
        :subtitle="`${enabledCount} item${enabledCount === 1 ? '' : 's'} · ${duration(totalSeconds)} loop`"
      >
        <template #actions>
          <div class="flex items-center gap-2">
            <AppButton variant="danger" size="sm" @click="confirmingDelete = true">Delete</AppButton>
            <!-- Explicitly saved, never autosaved: rearranging a live playlist must not push
                 half-finished states onto a wall of screens. -->
            <AppButton size="sm" :disabled="!isDirty" :loading="isSaving" @click="save">
              {{ isDirty ? 'Save' : 'Saved' }}
            </AppButton>
          </div>
        </template>
      </PageTitle>

      <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>
      <AppAlert v-if="deleteError" tone="danger">{{ deleteError }}</AppAlert>
      <AppAlert v-if="playlist.used_by.length">
        Playing on {{ playlist.used_by.join(', ') }}. Saved changes reach the screens within 30
        seconds.
      </AppAlert>

      <div class="flex items-center justify-between gap-4">
        <label class="flex items-center gap-2 text-sm text-ink-muted">
          <input
            type="checkbox"
            :checked="playlist.shuffle"
            class="size-4 accent-ink"
            @change="setShuffle(($event.target as HTMLInputElement).checked)"
          />
          Shuffle
        </label>
        <AppButton variant="secondary" size="sm" @click="picking = true">Add media</AppButton>
      </div>

      <!-- The media list comes first — it's what you're here to work on. Reference device,
           preview and Save follow, in that order, as the steps that come after placing items. -->
      <EmptyState
        v-if="!draft.length"
        title="This playlist is empty"
        description="Add media to build the loop. Items play top to bottom."
      >
        <template #actions>
          <AppButton size="sm" @click="picking = true">Add media</AppButton>
        </template>
      </EmptyState>

      <ul v-else class="flex flex-col gap-2">
        <li
          v-for="(row, index) in draft"
          :key="row.key"
          draggable="true"
          class="flex cursor-pointer items-center gap-3 rounded-xl bg-surface p-3
                 transition-colors duration-200"
          :class="[
            !row.isEnabled && 'opacity-50',
            dragFrom === index && 'bg-raised',
            preview.current.value?.key === row.key && 'bg-raised ring-2 ring-ink',
          ]"
          @dragstart="dragFrom = index"
          @dragover.prevent
          @drop.prevent="onDrop(index)"
          @dragend="dragFrom = null"
          @click="preview.select(row)"
        >
          <span class="cursor-grab select-none text-ink-subtle" aria-hidden="true">⠿</span>
          <span class="w-5 shrink-0 text-[13px] text-ink-subtle">{{ index + 1 }}</span>

          <div class="h-11 w-20 shrink-0 overflow-hidden rounded-md bg-raised">
            <img
              v-if="row.thumbnailUrl"
              :src="row.thumbnailUrl"
              :alt="row.filename"
              class="size-full object-cover"
            />
          </div>

          <div class="min-w-0 flex-1">
            <p class="truncate text-sm text-ink">{{ row.filename }}</p>
            <p class="text-[13px] text-ink-subtle">{{ row.kind }}</p>
          </div>

          <DurationInput v-model="row.durationSeconds" />

          <AppButton variant="ghost" size="sm" @click.stop="placing = row">
            Placement
          </AppButton>

          <AppButton variant="ghost" size="sm" @click="row.isEnabled = !row.isEnabled">
            {{ row.isEnabled ? 'Disable' : 'Enable' }}
          </AppButton>
          <AppButton variant="ghost" size="sm" @click="removeAt(index)">Remove</AppButton>
        </li>
      </ul>

      <!-- Reference device + preview. What every "Placement" edit above is aimed at, and
           the last check before Save. -->
      <div class="flex flex-col gap-3 rounded-xl bg-surface p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <select
              v-model="presetId"
              :disabled="isCustom"
              class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
                     focus:border-ink focus:outline-none disabled:opacity-40"
            >
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
              <input
                v-model.number="customWidth"
                type="number"
                min="1"
                class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       focus:border-ink focus:outline-none"
              />
              <span class="text-[13px] text-ink-subtle">×</span>
              <input
                v-model.number="customHeight"
                type="number"
                min="1"
                class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       focus:border-ink focus:outline-none"
              />
            </template>
          </div>
          <AppButton
            variant="secondary"
            size="sm"
            :disabled="!preview.enabled.value.length"
            @click="preview.toggle()"
          >
            {{ preview.isPlaying.value ? 'Pause' : 'Preview' }}
          </AppButton>
        </div>

        <ScreenPreview
          :screen-width="screen.width"
          :screen-height="screen.height"
          :src="preview.current.value?.url ?? null"
          :kind="preview.current.value?.kind ?? 'image'"
          :fit="preview.current.value?.fit ?? 'contain'"
          :media-width="preview.current.value?.mediaWidth ?? null"
          :media-height="preview.current.value?.mediaHeight ?? null"
          :crop-x="preview.current.value?.cropX ?? null"
          :crop-y="preview.current.value?.cropY ?? null"
          :crop-zoom="preview.current.value?.cropZoom ?? null"
          :trim-start-seconds="preview.current.value?.trimStartSeconds ?? 0"
          :trim-end-seconds="preview.current.value?.trimEndSeconds ?? null"
          :label="preview.current.value
            ? `${preview.current.value.filename} · ${screen.label}`
            : screen.label"
        />
      </div>
    </template>

    <AppModal v-if="picking" title="Add media" @close="picking = false">
      <p v-if="libraryLoading" class="text-sm text-ink-muted">Loading library…</p>
      <p v-else-if="!library.length" class="text-sm text-ink-muted">
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

    <AppModal v-if="placing" size="xl" @close="placing = null">
      <MediaPlacementEditor :row="placing" :reference-screen="screen" @apply="applyPlacement" @close="placing = null" />
    </AppModal>

    <AppModal v-if="confirmingDelete" title="Delete this playlist?" @close="confirmingDelete = false">
      <p class="text-sm text-ink-muted">
        {{ playlist?.name }} will be removed. The media it contains is not affected.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
