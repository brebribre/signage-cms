<script setup lang="ts">
/**
 * The notice at the top of every page when the account has expired, or is about to.
 *
 * Expired means read-only: people can sign in and look at everything, but the server refuses
 * every change. This says so once, up front, so nobody finds out by having a save fail. It
 * also says what keeps working (the screens), because that is the first worry.
 *
 * Nothing shows for an account with no end date, or one more than two weeks away.
 */
import IconEventBusy from '~icons/material-symbols/event-busy'
import IconSchedule from '~icons/material-symbols/schedule'

import { useAccountExpiry } from '@/hooks/useAccountExpiry'

const { isExpired, endsSoon, lastDay, daysLeft } = useAccountExpiry()
</script>

<template>
  <div
    v-if="isExpired"
    role="alert"
    class="mb-6 flex gap-3 rounded-2xl bg-red-50 px-4 py-3 text-sm text-danger ring-1 ring-red-200 ring-inset"
  >
    <IconEventBusy class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
    <div class="flex flex-col gap-1">
      <p class="font-medium">This account expired{{ lastDay ? ` after ${lastDay}` : '' }}</p>
      <p class="text-[13px] text-ink">
        You can still look at everything, but you can't make changes: no uploads, no editing or
        publishing, and no new screens. Your screens keep showing what they have now. Contact
        Paskall to renew.
      </p>
    </div>
  </div>

  <div
    v-else-if="endsSoon"
    role="status"
    class="mb-6 flex gap-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800 ring-1 ring-amber-200 ring-inset"
  >
    <IconSchedule class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
    <div class="flex flex-col gap-1">
      <p class="font-medium">
        This account is active until {{ lastDay }}{{ daysLeft !== null && daysLeft <= 1 ? ' (today)' : '' }}
      </p>
      <p class="text-[13px] text-ink">
        After that you can still look at everything, but you won't be able to make changes. Your
        screens will keep playing. Contact Paskall to renew.
      </p>
    </div>
  </div>
</template>
