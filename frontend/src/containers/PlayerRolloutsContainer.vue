<script setup lang="ts">
import { computed, ref } from 'vue'

import { useFormat } from '@/hooks/useFormat'
import { usePlayerRollouts } from '@/hooks/usePlayerRollouts'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import type { PlayerReleaseRead, PlayerRolloutRead } from '@/types/api'

const { releases, rollouts, isLoading, isSaving, error, schedule, cancel } = usePlayerRollouts()
const { bytes, date, dateTime } = useFormat()

const scheduling = ref<PlayerReleaseRead | null>(null)
const timing = ref<'now' | 'later'>('now')
const localDateTime = ref('')
const scheduleError = ref<string | null>(null)

function openSchedule(release: PlayerReleaseRead) {
  scheduling.value = release
  timing.value = 'now'
  localDateTime.value = ''
  scheduleError.value = null
}

async function onConfirmSchedule() {
  if (!scheduling.value) return
  scheduleError.value = null
  let scheduledAt: string | null = null
  if (timing.value === 'later') {
    if (!localDateTime.value) {
      scheduleError.value = 'Pick a date and time.'
      return
    }
    // A bare "YYYY-MM-DDTHH:MM" from <input type="datetime-local"> has no offset — the
    // Date constructor reads it as this browser's local time, which is what the person
    // picking it actually meant.
    const asDate = new Date(localDateTime.value)
    if (asDate.getTime() <= Date.now()) {
      scheduleError.value = 'Pick a time in the future — for right now, use "Now" instead.'
      return
    }
    scheduledAt = asDate.toISOString()
  }
  const ok = await schedule(scheduling.value.version, scheduledAt)
  if (ok) scheduling.value = null
}

function isUpcoming(r: PlayerRolloutRead): boolean {
  return !r.is_active && new Date(r.scheduled_at).getTime() > Date.now()
}

const confirmingCancel = ref<PlayerRolloutRead | null>(null)
async function onCancel() {
  if (confirmingCancel.value && (await cancel(confirmingCancel.value.id))) {
    confirmingCancel.value = null
  }
}

const activeRollout = computed(() => rollouts.value.find((r) => r.is_active) ?? null)
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Player Updates"
      subtitle="Which build every screen runs, and when a new one takes over."
    />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <template v-else>
      <AppCard v-if="activeRollout">
        <p class="text-[13px] text-ink-muted">Currently live</p>
        <p class="mt-0.5 text-sm text-ink">
          {{ activeRollout.version }}
          <span class="text-ink-muted">— since {{ dateTime(activeRollout.scheduled_at) }}</span>
        </p>
      </AppCard>

      <div class="flex flex-col gap-2">
        <h2 class="text-lg">Releases</h2>
        <p class="text-[13px] text-ink-muted">
          Every build <code class="text-ink-subtle">publish_player_apk.py</code> has uploaded.
          Schedule one to roll it out — now, or at a specific time.
        </p>

        <EmptyState
          v-if="!releases.length"
          title="No builds uploaded yet"
          description="Run publish_player_apk.py to upload one before it can be scheduled."
        />
        <ul v-else class="flex flex-col gap-2">
          <li v-for="r in releases" :key="r.version">
            <AppCard>
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-sm text-ink">
                    {{ r.version }}
                    <span v-if="r.is_current" class="text-ink-subtle"> · current</span>
                  </p>
                  <p class="mt-0.5 text-[13px] text-ink-muted">
                    {{ date(r.uploaded_at) }} · {{ bytes(r.size_bytes) }}
                  </p>
                </div>
                <AppButton size="sm" variant="secondary" @click="openSchedule(r)">
                  Schedule rollout
                </AppButton>
              </div>
            </AppCard>
          </li>
        </ul>
      </div>

      <div class="flex flex-col gap-2 border-t border-line pt-6">
        <h2 class="text-lg">Rollout history</h2>
        <p class="text-[13px] text-ink-muted">
          Past and upcoming together — the most recently scheduled one whose time has passed
          is always what's live.
        </p>

        <EmptyState
          v-if="!rollouts.length"
          title="No rollouts yet"
          description="Schedule a release above to start the timeline."
        />
        <ul v-else class="flex flex-col gap-2">
          <li v-for="r in rollouts" :key="r.id">
            <AppCard>
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-sm text-ink">
                    {{ r.version }}
                    <span v-if="r.is_active" class="text-ink-subtle"> · active now</span>
                    <span v-else-if="isUpcoming(r)" class="text-ink-subtle"> · scheduled</span>
                  </p>
                  <p class="mt-0.5 text-[13px] text-ink-muted">
                    {{ isUpcoming(r) ? 'Takes over' : 'Took over' }} {{ dateTime(r.scheduled_at) }}
                  </p>
                </div>
                <AppButton
                  v-if="isUpcoming(r)"
                  size="sm" variant="danger"
                  @click="confirmingCancel = r"
                >
                  Cancel
                </AppButton>
              </div>
            </AppCard>
          </li>
        </ul>
      </div>
    </template>

    <AppModal
      v-if="scheduling"
      :title="`Schedule ${scheduling.version}`"
      @close="scheduling = null"
    >
      <form class="flex flex-col gap-3" @submit.prevent="onConfirmSchedule">
        <div class="flex gap-2">
          <button
            type="button"
            class="rounded-full border-2 px-3 py-1 text-[13px] transition-colors duration-200"
            :class="timing === 'now'
              ? 'border-ink bg-ink text-ink-inverse'
              : 'border-line-strong text-ink-muted hover:bg-raised'"
            @click="timing = 'now'"
          >
            Now
          </button>
          <button
            type="button"
            class="rounded-full border-2 px-3 py-1 text-[13px] transition-colors duration-200"
            :class="timing === 'later'
              ? 'border-ink bg-ink text-ink-inverse'
              : 'border-line-strong text-ink-muted hover:bg-raised'"
            @click="timing = 'later'"
          >
            Later
          </button>
        </div>

        <div v-if="timing === 'now'" class="rounded-lg bg-surface px-3 py-2 text-[13px] text-ink-muted">
          Every screen picks this up on its next heartbeat — usually within 30 seconds.
        </div>
        <div v-else class="flex flex-col gap-1.5">
          <label class="text-[13px] text-ink-muted">Date and time</label>
          <input
            v-model="localDateTime"
            type="datetime-local"
            class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                   focus:border-ink focus:outline-none"
          />
          <p class="text-[13px] text-ink-subtle">In your own browser's timezone.</p>
        </div>

        <AppAlert v-if="scheduleError" tone="danger">{{ scheduleError }}</AppAlert>

        <div class="mt-1 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" type="button" @click="scheduling = null">
            Cancel
          </AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">
            {{ timing === 'now' ? 'Roll out now' : 'Schedule' }}
          </AppButton>
        </div>
      </form>
    </AppModal>

    <AppModal
      v-if="confirmingCancel"
      title="Cancel this rollout?"
      @close="confirmingCancel = null"
    >
      <p class="text-sm text-ink-muted">
        {{ confirmingCancel.version }}, scheduled for {{ dateTime(confirmingCancel.scheduled_at) }},
        will not take effect. Screens stay on whatever is currently live.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingCancel = null">Keep it</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onCancel">
          Cancel rollout
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
