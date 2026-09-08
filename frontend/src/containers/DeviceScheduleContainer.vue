<script setup lang="ts">
import { computed, ref } from 'vue'

import { useFormat } from '@/hooks/useFormat'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useSchedules } from '@/hooks/useSchedules'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { ScheduleRead } from '@/types/api'

const props = defineProps<{ deviceId: string; timezone: string }>()

const { schedules, resolution, isLoading, isSaving, error, formError, create, update, remove } =
  useSchedules(props.deviceId)
const { items: playlists } = usePlaylists()

const adding = ref(false)
const confirmingDelete = ref<ScheduleRead | null>(null)
const form = ref({
  playlist_id: '',
  name: '',
  days_of_week: WEEKDAYS,
  starts_at: '09:00',
  ends_at: '17:00',
  priority: 0,
})

function toggleDay(bit: number) {
  form.value.days_of_week ^= bit
}

function dayLabel(mask: number): string {
  if (mask === ALL_DAYS) return 'Every day'
  if (mask === WEEKDAYS) return 'Weekdays'
  if (mask === WEEKENDS) return 'Weekends'
  return DAY_BITS.filter((d) => mask & d.bit).map((d) => d.short).join(', ')
}

/** "09:00:00" → "09:00". The seconds are always zero and only add noise. */
const hhmm = (t: string) => t.slice(0, 5)

/** A window whose end is at or before its start runs through midnight. */
function crossesMidnight(s: ScheduleRead) {
  return s.ends_at <= s.starts_at
}

const playlistName = (id: string) => playlists.value.find((p) => p.id === id)?.name ?? '—'

const nowPlaying = computed(() => {
  if (!resolution.value) return null
  return {
    playlist: resolution.value.playlist_id
      ? playlistName(resolution.value.playlist_id)
      : 'Nothing assigned',
    why: resolution.value.schedule_name
      ? `via schedule “${resolution.value.schedule_name}”`
      : 'the default playlist',
    localTime: new Date(resolution.value.device_local_time).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    }),
  }
})

async function onCreate() {
  const ok = await create({
    playlist_id: form.value.playlist_id,
    name: form.value.name,
    days_of_week: form.value.days_of_week,
    // The backend wants seconds; the browser's time input gives HH:MM.
    starts_at: `${form.value.starts_at}:00`,
    ends_at: `${form.value.ends_at}:00`,
    priority: form.value.priority,
  })
  if (ok) {
    adding.value = false
    form.value = {
      playlist_id: '', name: '', days_of_week: WEEKDAYS,
      starts_at: '09:00', ends_at: '17:00', priority: 0,
    }
  }
}

async function onDelete() {
  if (confirmingDelete.value && (await remove(confirmingDelete.value.id))) {
    confirmingDelete.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-lg">Schedule</h2>
        <p class="mt-0.5 text-[13px] text-ink-muted">
          Overrides the default playlist during set hours. Times are local to the screen
          ({{ timezone }}).
        </p>
      </div>
      <AppButton size="sm" :disabled="!playlists.length" @click="adding = true">
        Add rule
      </AppButton>
    </div>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

    <!-- The question anyone editing a schedule actually has, answered without waiting for
         the window to come round. -->
    <AppCard v-if="nowPlaying">
      <p class="text-[13px] text-ink-muted">Playing now — {{ nowPlaying.localTime }} on the screen</p>
      <p class="mt-0.5 text-sm text-ink">
        {{ nowPlaying.playlist }}
        <span class="text-ink-muted">{{ nowPlaying.why }}</span>
      </p>
    </AppCard>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!schedules.length"
      title="No schedule rules"
      :description="playlists.length
        ? 'This screen plays its default playlist around the clock.'
        : 'Create a playlist first — a rule needs something to switch to.'"
    />

    <ul v-else class="flex flex-col gap-2">
      <li v-for="s in schedules" :key="s.id">
        <AppCard>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0" :class="!s.is_enabled && 'opacity-50'">
              <p class="truncate text-sm text-ink">
                {{ s.name || playlistName(s.playlist_id) }}
                <span v-if="!s.is_enabled" class="text-ink-subtle"> · paused</span>
              </p>
              <p class="mt-0.5 text-[13px] text-ink-muted">
                {{ dayLabel(s.days_of_week) }} ·
                {{ hhmm(s.starts_at) }}–{{ hhmm(s.ends_at) }}
                <span v-if="crossesMidnight(s)" class="text-ink-subtle">(next day)</span>
                · plays {{ playlistName(s.playlist_id) }}
                <span v-if="s.priority"> · priority {{ s.priority }}</span>
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-1">
              <AppButton
                variant="ghost"
                size="sm"
                :loading="isSaving"
                @click="update(s.id, { is_enabled: !s.is_enabled })"
              >
                {{ s.is_enabled ? 'Pause' : 'Resume' }}
              </AppButton>
              <AppButton variant="danger" size="sm" @click="confirmingDelete = s">Delete</AppButton>
            </div>
          </div>
        </AppCard>
      </li>
    </ul>

    <AppModal v-if="adding" title="Add a schedule rule" @close="adding = false">
      <form class="flex flex-col gap-3" @submit.prevent="onCreate">
        <div class="flex flex-col gap-1.5">
          <label class="text-[13px] text-ink-muted">Playlist</label>
          <select
            v-model="form.playlist_id"
            required
            class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                   focus:border-ink focus:outline-none"
          >
            <option value="" disabled>Choose a playlist</option>
            <option v-for="p in playlists" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <AppInput id="sched-name" v-model="form.name" label="Name" placeholder="Breakfast menu" />

        <div class="flex flex-col gap-1.5">
          <label class="text-[13px] text-ink-muted">Days</label>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="d in DAY_BITS"
              :key="d.bit"
              type="button"
              class="rounded-full border-2 px-2.5 py-1 text-[13px] transition-colors duration-200"
              :class="form.days_of_week & d.bit
                ? 'border-ink bg-ink text-ink-inverse'
                : 'border-line-strong text-ink-muted hover:bg-raised'"
              @click="toggleDay(d.bit)"
            >
              {{ d.short }}
            </button>
          </div>
          <div class="mt-1 flex gap-2">
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="form.days_of_week = WEEKDAYS">Weekdays</button>
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="form.days_of_week = WEEKENDS">Weekends</button>
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="form.days_of_week = ALL_DAYS">Every day</button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">From</label>
            <input v-model="form.starts_at" type="time" required
                   class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                          text-ink focus:border-ink focus:outline-none" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">Until</label>
            <input v-model="form.ends_at" type="time" required
                   class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                          text-ink focus:border-ink focus:outline-none" />
          </div>
        </div>
        <p v-if="form.ends_at <= form.starts_at" class="text-[13px] text-ink-subtle">
          This window runs through midnight into the next day.
        </p>

        <AppInput
          id="sched-priority"
          v-model="form.priority as unknown as string"
          type="number"
          label="Priority"
          hint="Higher wins where rules overlap. Leave at 0 unless you need one to take over another."
        />

        <div class="mt-1 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">
            Cancel
          </AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving" :disabled="!form.playlist_id">
            Add rule
          </AppButton>
        </div>
      </form>
    </AppModal>

    <AppModal v-if="confirmingDelete" title="Delete this rule?" @close="confirmingDelete = null">
      <p class="text-sm text-ink-muted">
        The screen will fall back to its default playlist during those hours.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = null">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
