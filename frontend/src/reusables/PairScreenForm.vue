<script setup lang="ts">
/** Claiming a screen by the code it shows — shared by the Devices page and the deploy flow.
 *  Owns only its own fields; the claim itself and the handshake state come from the caller's
 *  `useDevices()`, so whichever page opened this sees the new screen in its own list. */
import { computed, ref } from 'vue'

import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import ConnectAnimation from '@/reusables/ConnectAnimation.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import type { ClaimBody } from '@/types/api'

const props = defineProps<{
  isSaving: boolean
  claimError: string | null
  connecting: { id: string; name: string; connected: boolean } | null
}>()
const emit = defineEmits<{ submit: [body: ClaimBody]; cancel: [] }>()

const form = ref({ pairing_code: '', name: '', location: '' })

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
  <form class="flex flex-col gap-3" @submit.prevent="onSubmit">
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
      <p v-else-if="handshake === 'connected'" class="text-[13px] text-ink">
        {{ connecting?.name }} connected
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
