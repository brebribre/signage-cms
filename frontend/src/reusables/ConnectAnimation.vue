<script setup lang="ts">
/** Cloud → screen, while a newly claimed screen collects its credential: dots travel toward the
 *  TV while waiting, the line settles green with a check once it has connected, or a red cross
 *  marks the TV if it didn't. Presentational only — handed a state, knows nothing about pairing. */
import IconCheck from '~icons/material-symbols/check'
import IconClose from '~icons/material-symbols/close'
import IconCloud from '~icons/material-symbols/cloud-outline'
import IconTv from '~icons/material-symbols/tv-outline'

defineProps<{ state: 'connecting' | 'connected' | 'failed' }>()

const LABEL = { connecting: 'Connecting', connected: 'Connected', failed: 'Not connected' } as const
</script>

<template>
  <div class="flex items-center justify-center gap-3 py-2" role="status" :aria-label="LABEL[state]">
    <span
      class="flex size-12 shrink-0 items-center justify-center rounded-full bg-raised text-ink"
      :class="state === 'connecting' && 'cloud-pulse'"
    >
      <IconCloud class="size-6" />
    </span>

    <div class="relative flex h-3 w-24 items-center">
      <span
        class="h-0.5 w-full rounded-full transition-colors duration-300"
        :class="state === 'connected' ? 'bg-emerald-600' : 'bg-line'"
      />
      <template v-if="state === 'connecting'">
        <span
          v-for="i in 3"
          :key="i"
          class="travel-dot absolute top-1/2 size-1.5 rounded-full bg-ink"
          :style="{ animationDelay: `${(i - 1) * 0.4}s` }"
        />
      </template>
    </div>

    <span class="relative flex size-12 shrink-0 items-center justify-center rounded-full bg-raised text-ink">
      <IconTv class="size-6" />
      <span
        v-if="state === 'connected'"
        class="badge-pop absolute -right-1 -bottom-1 flex size-5 items-center justify-center rounded-full
               bg-emerald-600 text-white ring-2 ring-canvas"
      >
        <IconCheck class="size-3.5" />
      </span>
      <span
        v-else-if="state === 'failed'"
        class="badge-pop absolute -right-1 -bottom-1 flex size-5 items-center justify-center rounded-full
               bg-danger text-white ring-2 ring-canvas"
      >
        <IconClose class="size-3.5" />
      </span>
    </span>
  </div>
</template>

<style scoped>
.cloud-pulse {
  animation: cloud-pulse 1.6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes cloud-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.7; }
}

.travel-dot {
  left: 0;
  opacity: 0;
  translate: -50% -50%;
  animation: travel 1.2s linear infinite;
}
@keyframes travel {
  0% { left: 0; opacity: 0; }
  15% { opacity: 1; }
  85% { opacity: 1; }
  100% { left: 100%; opacity: 0; }
}

.badge-pop {
  animation: badge-pop 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes badge-pop {
  0% { transform: scale(0); }
  70% { transform: scale(1.15); }
  100% { transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .cloud-pulse, .badge-pop { animation: none; }
  .travel-dot { animation-duration: 2.4s; }
}
</style>
