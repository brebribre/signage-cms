<script setup lang="ts">
/** Claiming a screen by the code it shows — shared by the Devices page and the deploy flow.
 *  Owns only its own fields; the claim itself and the handshake state come from the caller's
 *  `useDevices()`, so whichever page opened this sees the new screen in its own list. */
import { ref } from 'vue'

import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import type { ClaimBody } from '@/types/api'

defineProps<{
  isSaving: boolean
  claimError: string | null
  connecting: { id: string; name: string; connected: boolean } | null
}>()
const emit = defineEmits<{ submit: [body: ClaimBody]; cancel: [] }>()

const form = ref({ pairing_code: '', name: '', location: '' })
</script>

<template>
  <form class="flex flex-col gap-3" @submit.prevent="emit('submit', { ...form })">
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
    <AppAlert v-if="claimError" tone="danger">{{ claimError }}</AppAlert>

    <!-- The handshake, shown as it happens. The claim returns instantly but the screen only
         learns about it on its next poll, so "created" alone sends people away from a screen
         that has not started yet. -->
    <div
      v-if="isSaving && connecting"
      class="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-[13px] text-ink-muted"
    >
      <span class="size-2 shrink-0 animate-pulse rounded-full bg-ink" aria-hidden="true" />
      Waiting for {{ connecting.name }} to connect…
    </div>
    <div v-else-if="connecting?.connected" class="rounded-lg bg-surface px-3 py-2 text-[13px] text-ink">
      {{ connecting.name }} connected.
    </div>

    <div class="mt-1 flex justify-end gap-2">
      <AppButton variant="secondary" size="sm" type="button" @click="emit('cancel')">Cancel</AppButton>
      <AppButton size="sm" type="submit" :loading="isSaving">
        {{ isSaving && connecting ? 'Connecting…' : 'Add screen' }}
      </AppButton>
    </div>
  </form>
</template>
