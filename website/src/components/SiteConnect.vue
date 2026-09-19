<script setup lang="ts">
/** Every screen, whatever it runs on, answering to one place. */
import ConnectedFleet from './ConnectedFleet.vue'
</script>

<template>
  <section id="connect" class="bg-page py-20 sm:py-28">
    <div class="mx-auto max-w-5xl px-5 sm:px-8">
      <div class="reveal mx-auto max-w-2xl text-center">
        <p class="text-[13px] font-medium uppercase tracking-wider text-brand">Screens</p>
        <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">Connect your screens.</h2>
        <p class="mt-4 leading-relaxed text-ink-muted">
          One code. Any screen. Android boxes, smart TVs and browsers become one fleet.
        </p>
      </div>
      <div class="reveal mt-14">
        <ConnectedFleet />
      </div>
    </div>
  </section>
</template>
