<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCampaignDetail } from '@/hooks/useCampaignDetail'
import { useDevices } from '@/hooks/useDevices'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { CampaignRuleWrite } from '@/types/api'

const route = useRoute()
const router = useRouter()
// Absent on /campaigns/new — that is what puts this whole page in create mode.
const id = typeof route.params.id === 'string' ? route.params.id : null

const { campaign, isLoading, isSaving, isDeleting, error, saveError, skippedDeviceIds, save, remove } =
  useCampaignDetail(id)
const { items: devices, isLoading: devicesLoading } = useDevices()
const { items: playlists } = usePlaylists()

// Everything below is a draft. Nothing is written until "Save" — the same reasoning as every
// other device-affecting form in this app, just covering many devices instead of one.
const name = ref('')
const deviceIds = ref<string[]>([])
/** Local, HH:MM local-rule shape — converted to the API's HH:MM:SS on save. Editing rebuilds
 *  this from the loaded campaign, same as every other detail form here. */
type LocalRule = { playlist_id: string; name: string; days_of_week: number; starts_at: string; ends_at: string; priority: number }
const rules = ref<LocalRule[]>([])

watch(campaign, (c) => {
  if (!c) return
  name.value = c.name
  deviceIds.value = [...c.device_ids]
  rules.value = c.rules.map((r) => ({
    playlist_id: r.playlist_id, name: r.name, days_of_week: r.days_of_week,
    starts_at: r.starts_at.slice(0, 5), ends_at: r.ends_at.slice(0, 5), priority: r.priority,
  }))
}, { immediate: true })

function toggleDevice(deviceId: string) {
  const at = deviceIds.value.indexOf(deviceId)
  at >= 0 ? deviceIds.value.splice(at, 1) : deviceIds.value.push(deviceId)
}

const allDevicesSelected = computed(
  () => devices.value.length > 0 && deviceIds.value.length === devices.value.length
)
function toggleAllDevices() {
  deviceIds.value = allDevicesSelected.value ? [] : devices.value.map((d) => d.id)
}

const playlistName = (playlistId: string) => playlists.value.find((p) => p.id === playlistId)?.name ?? '—'

function dayLabel(mask: number): string {
  if (mask === ALL_DAYS) return 'Every day'
  if (mask === WEEKDAYS) return 'Weekdays'
  if (mask === WEEKENDS) return 'Weekends'
  return DAY_BITS.filter((d) => mask & d.bit).map((d) => d.short).join(', ')
}
const crossesMidnight = (r: LocalRule) => r.ends_at <= r.starts_at

// Rule editor: one modal for both adding a new rule and editing an existing one, keyed by
// index — null means "adding", a number means "replace the rule at this index".
const editingIndex = ref<number | null>(null)
const ruleForm = reactive<LocalRule>({
  playlist_id: '', name: '', days_of_week: WEEKDAYS, starts_at: '09:00', ends_at: '17:00', priority: 0,
})

function openAddRule() {
  editingIndex.value = null
  Object.assign(ruleForm, {
    playlist_id: '', name: '', days_of_week: WEEKDAYS, starts_at: '09:00', ends_at: '17:00', priority: 0,
  })
}
function openEditRule(index: number) {
  editingIndex.value = index
  Object.assign(ruleForm, rules.value[index])
}
function toggleRuleDay(bit: number) {
  ruleForm.days_of_week ^= bit
}
function saveRule() {
  const rule: LocalRule = { ...ruleForm }
  if (editingIndex.value === null) rules.value.push(rule)
  else rules.value.splice(editingIndex.value, 1, rule)
  editingIndex.value = null
  ruleAdding.value = false
}
function removeRule(index: number) {
  rules.value.splice(index, 1)
}
const ruleAdding = ref(false)

const canSave = computed(
  () => name.value.trim().length > 0 && deviceIds.value.length > 0 && rules.value.length > 0
)

async function onSave() {
  const body = {
    name: name.value,
    device_ids: deviceIds.value,
    rules: rules.value.map((r): CampaignRuleWrite => ({
      playlist_id: r.playlist_id,
      name: r.name,
      days_of_week: r.days_of_week,
      starts_at: `${r.starts_at}:00`,
      ends_at: `${r.ends_at}:00`,
      priority: r.priority,
    })),
  }
  const savedId = await save(body)
  // Only leave if nothing was skipped — a skipped device is worth reading before moving on,
  // same as any other partial-success result in this app.
  if (savedId && !skippedDeviceIds.value.length) router.push({ name: 'campaigns' })
}

const confirmingDelete = ref(false)
async function onDelete() {
  if (await remove()) router.push({ name: 'campaigns' })
  else confirmingDelete.value = false
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'campaigns' })">
      ← Campaigns
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else>
      <PageTitle :title="id ? 'Edit campaign' : 'New campaign'">
        <template #actions>
          <AppButton v-if="id" variant="danger" size="sm" @click="confirmingDelete = true">
            Delete
          </AppButton>
        </template>
      </PageTitle>

      <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>
      <AppAlert v-if="skippedDeviceIds.length" tone="danger">
        Saved, but {{ skippedDeviceIds.length }} selected screen{{ skippedDeviceIds.length === 1 ? '' : 's' }}
        could not be reached and were left out.
      </AppAlert>

      <AppInput id="campaign-name" v-model="name" label="Name" placeholder="Lobby rotation" required />

      <!-- Devices -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <h2 class="text-lg">Screens</h2>
          <label
            v-if="devices.length"
            class="flex cursor-pointer items-center gap-2 text-[13px] text-ink-muted"
          >
            <input
              type="checkbox" class="size-4 accent-ink" :checked="allDevicesSelected"
              @change="toggleAllDevices"
            />
            Select all
          </label>
        </div>
        <p class="text-[13px] text-ink-muted">
          Every screen picked here plays this campaign's rules. A screen in more than one
          campaign resolves overlapping rules by priority, same as a single screen's schedule.
        </p>

        <p v-if="devicesLoading" class="text-sm text-ink-muted">Loading…</p>
        <EmptyState v-else-if="!devices.length" title="No screens yet"
                    description="Pair a screen first — a campaign needs something to target." />
        <ul v-else class="max-h-64 overflow-y-auto rounded-lg border border-line">
          <li v-for="d in devices" :key="d.id" class="border-b border-line last:border-b-0">
            <label class="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-surface">
              <input
                type="checkbox" class="size-4 shrink-0 accent-ink"
                :checked="deviceIds.includes(d.id)"
                @change="toggleDevice(d.id)"
              />
              <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ d.name || 'Unnamed screen' }}</span>
              <span v-if="d.location" class="shrink-0 text-[13px] text-ink-subtle">{{ d.location }}</span>
            </label>
          </li>
        </ul>
      </div>

      <!-- Rules -->
      <div class="flex flex-col gap-2 border-t border-line pt-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg">Rules</h2>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              One playlist per rule. Add more than one to switch by schedule — the highest
              priority window covering the moment wins.
            </p>
          </div>
          <AppButton size="sm" :disabled="!playlists.length" @click="ruleAdding = true; openAddRule()">
            Add rule
          </AppButton>
        </div>

        <EmptyState
          v-if="!rules.length"
          title="No rules yet"
          :description="playlists.length
            ? 'Add at least one playlist-and-schedule rule for this campaign to do anything.'
            : 'Create a playlist first — a rule needs something to play.'"
        />
        <ul v-else class="flex flex-col gap-2">
          <li v-for="(r, i) in rules" :key="i">
            <AppCard interactive @click="ruleAdding = true; openEditRule(i)">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="min-w-0">
                  <p class="truncate text-sm text-ink">{{ r.name || playlistName(r.playlist_id) }}</p>
                  <p class="mt-0.5 text-[13px] text-ink-muted">
                    {{ dayLabel(r.days_of_week) }} · {{ r.starts_at }}–{{ r.ends_at }}
                    <span v-if="crossesMidnight(r)" class="text-ink-subtle">(next day)</span>
                    · plays {{ playlistName(r.playlist_id) }}
                    <span v-if="r.priority"> · priority {{ r.priority }}</span>
                  </p>
                </div>
                <AppButton variant="ghost" size="sm" @click.stop="removeRule(i)">Remove</AppButton>
              </div>
            </AppCard>
          </li>
        </ul>
      </div>

      <div class="mt-1 flex items-center gap-3 border-t border-line pt-6">
        <AppButton :disabled="!canSave" :loading="isSaving" @click="onSave">
          {{ id ? 'Save changes' : 'Create campaign' }}
        </AppButton>
        <span v-if="!canSave" class="text-[13px] text-ink-subtle">
          Needs a name, at least one screen, and at least one rule.
        </span>
      </div>
    </template>

    <!-- Add/edit rule -->
    <AppModal v-if="ruleAdding" :title="editingIndex === null ? 'Add a rule' : 'Edit rule'" @close="ruleAdding = false">
      <form class="flex flex-col gap-3" @submit.prevent="saveRule">
        <div class="flex flex-col gap-1.5">
          <label class="text-[13px] text-ink-muted">Playlist</label>
          <select
            v-model="ruleForm.playlist_id"
            required
            class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                   focus:border-ink focus:outline-none"
          >
            <option value="" disabled>Choose a playlist</option>
            <option v-for="p in playlists" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <AppInput id="rule-name" v-model="ruleForm.name" label="Name" placeholder="Breakfast menu" />

        <div class="flex flex-col gap-1.5">
          <label class="text-[13px] text-ink-muted">Days</label>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="d in DAY_BITS"
              :key="d.bit"
              type="button"
              class="rounded-full border-2 px-2.5 py-1 text-[13px] transition-colors duration-200"
              :class="ruleForm.days_of_week & d.bit
                ? 'border-ink bg-ink text-ink-inverse'
                : 'border-line-strong text-ink-muted hover:bg-raised'"
              @click="toggleRuleDay(d.bit)"
            >
              {{ d.short }}
            </button>
          </div>
          <div class="mt-1 flex gap-2">
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="ruleForm.days_of_week = WEEKDAYS">Weekdays</button>
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="ruleForm.days_of_week = WEEKENDS">Weekends</button>
            <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                    @click="ruleForm.days_of_week = ALL_DAYS">Every day</button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">From</label>
            <input v-model="ruleForm.starts_at" type="time" required
                   class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                          text-ink focus:border-ink focus:outline-none" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">Until</label>
            <input v-model="ruleForm.ends_at" type="time" required
                   class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                          text-ink focus:border-ink focus:outline-none" />
          </div>
        </div>
        <p v-if="ruleForm.ends_at <= ruleForm.starts_at" class="text-[13px] text-ink-subtle">
          This window runs through midnight into the next day.
        </p>

        <AppInput
          id="rule-priority"
          v-model="ruleForm.priority as unknown as string"
          type="number"
          label="Priority"
          hint="Higher wins where rules overlap. Leave at 0 unless you need one to take over another."
        />

        <div class="mt-1 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" type="button" @click="ruleAdding = false">
            Cancel
          </AppButton>
          <AppButton size="sm" type="submit" :disabled="!ruleForm.playlist_id">
            {{ editingIndex === null ? 'Add rule' : 'Save rule' }}
          </AppButton>
        </div>
      </form>
    </AppModal>

    <AppModal v-if="confirmingDelete" title="Delete this campaign?" @close="confirmingDelete = false">
      <p class="text-sm text-ink-muted">
        Every screen in this campaign falls back to its default playlist (or another campaign
        covering it) for whatever time this one used to control.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isDeleting" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
