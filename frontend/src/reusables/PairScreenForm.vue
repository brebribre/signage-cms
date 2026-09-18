<script setup lang="ts">
/** Claiming a screen by the code it shows — shared by the Screens page and the deploy flow.
 *  Owns only its own fields; the claim itself and the handshake state come from the caller's
 *  `useDevices()`, so whichever page opened this sees the new screen in its own list. */
import { computed, ref } from 'vue'
import IconTv from '~icons/material-symbols/tv-outline'

import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import ConnectAnimation from '@/reusables/ConnectAnimation.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import type { ClaimBody, DeviceOrientation } from '@/types/api'
import { ORIENTATIONS } from '@/utils/orientation'

const props = defineProps<{
  isSaving: boolean
  claimError: string | null
  connecting: { id: string; name: string; connected: boolean } | null
}>()
const emit = defineEmits<{
  submit: [body: ClaimBody]
  cancel: []
  /** The screen is connected and its mounting has been chosen — the caller saves it and
   *  moves on. Null when the person skipped the question (the default, 90°, stays). */
  done: [orientation: DeviceOrientation | null]
}>()

const form = ref({ pairing_code: '', name: '', location: '' })
/** Asked once the screen has connected: a totem stood on the wrong side shows everything
 *  upside down, and the moment it's paired is when someone is actually looking at it. */
const orientation = ref<DeviceOrientation>('90')

/** The handshake only shows once this form has actually been submitted — `claimError` and
 *  `connecting` live in the caller's hook and can be left over from an earlier attempt. */
const submitted = ref(false)

function onSubmit() {
  submitted.value = true
  emit('submit', { ...form.value })
}

/** The claim returns instantly but the screen only learns about it on its next poll, so
 *  "created" alone sends people away from a screen that has not started yet — the handshake
 *  is shown as it happens. */
const handshake = computed<'connecting' | 'connected' | 'failed' | null>(() => {
  if (!submitted.value) return null
  if (props.isSaving) return 'connecting'
  if (props.connecting?.connected) return 'connected'
  if (props.claimError) return 'failed'
  return null
})
</script>

<template>
  <!-- Connected: the one question left is how the panel is mounted. -->
  <div v-if="handshake === 'connected'" class="flex flex-col gap-3">
    <div class="flex flex-col items-center gap-1 rounded-lg bg-surface px-3 py-3">
      <ConnectAnimation state="connected" />
      <p class="text-[13px] text-ink">{{ connecting?.name }} connected</p>
    </div>
    <p class="text-sm text-ink">How is the screen mounted?</p>
    <p class="text-[13px] text-ink-muted">
      The screen turns what it shows to match. Pick the one where the top of the picture
      would be at the top of the panel.
    </p>
    <div class="grid grid-cols-4 gap-2" role="radiogroup" aria-label="Orientation">
      <button
        v-for="o in ORIENTATIONS"
        :key="o.value"
        type="button"
        role="radio"
        :aria-checked="orientation === o.value"
        class="flex flex-col items-center gap-2 rounded-xl border px-2 py-3 text-center transition-colors duration-150"
        :class="orientation === o.value ? 'border-ink bg-ink text-ink-inverse' : 'border-line-strong text-ink hover:bg-raised'"
        @click="orientation = o.value"
      >
        <span class="flex size-10 items-center justify-center">
          <IconTv class="size-8 transition-transform duration-200" :style="{ transform: `rotate(${o.value}deg)` }" aria-hidden="true" />
        </span>
        <span class="text-sm">{{ o.label }}</span>
        <span class="text-[11px] leading-tight" :class="orientation === o.value ? 'text-ink-inverse/80' : 'text-ink-muted'">{{ o.hint }}</span>
      </button>
    </div>
    <AppAlert v-if="claimError" tone="danger">{{ claimError }}</AppAlert>
    <ModalActions>
      <AppButton variant="secondary" size="sm" type="button" :disabled="isSaving" @click="emit('done', null)">Skip</AppButton>
      <AppButton size="sm" type="button" :loading="isSaving" @click="emit('done', orientation)">Done</AppButton>
    </ModalActions>
  </div>

  <form v-else class="flex flex-col gap-3" @submit.prevent="onSubmit">
    <p class="text-[13px] text-ink-muted">
      Type the code shown on the screen. Codes expire after 15 minutes.
    </p>
    <AppInput
      id="pair-code"
      v-model="form.pairing_code"
      label="Pairing code"
      placeholder="ABCDEF"
      required
      hint="Not case-sensitive"
    />
    <AppInput id="pair-name" v-model="form.name" label="Name" placeholder="Lobby" required />
    <AppInput id="pair-location" v-model="form.location" label="Location" placeholder="Ground floor" />

    <div v-if="handshake" class="flex flex-col items-center gap-1 rounded-lg bg-surface px-3 py-3">
      <ConnectAnimation :state="handshake" />
      <p v-if="handshake === 'connecting'" class="text-[13px] text-ink-muted">
        {{ connecting ? `Waiting for ${connecting.name} to connect…` : 'Connecting…' }}
      </p>
    </div>

    <AppAlert v-if="claimError" tone="danger">{{ claimError }}</AppAlert>

    <ModalActions>
      <AppButton variant="secondary" size="sm" type="button" @click="emit('cancel')">Cancel</AppButton>
      <AppButton size="sm" type="submit" :loading="isSaving">
        {{ isSaving && connecting ? 'Connecting…' : 'Add screen' }}
      </AppButton>
    </ModalActions>
  </form>
</template>
