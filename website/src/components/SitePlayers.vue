<script setup lang="ts">
import ConnectedFleet from './ConnectedFleet.vue'
</script>

<template>
  <!-- The dark stretch, entered on a diagonal: the change of pace between what Paskall is and
       what it runs. -->
  <section id="players" class="angled-band angled-band-up relative -mt-[7vw] text-ink-inverse">
    <div class="relative mx-auto max-w-5xl px-5 pt-[calc(7vw+5rem)] pb-24 sm:px-8 sm:pb-28">
      <div class="reveal mx-auto max-w-2xl text-center">
        <p class="text-[13px] font-medium uppercase tracking-wider text-white/70">Players</p>
        <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">One code. Any screen.</h2>
        <p class="mt-4 text-white/80">
          Android boxes, smart TVs, any browser. They all pair with a six letter code and answer to
          the same dashboard.
        </p>
      </div>
      <div class="reveal mt-14">
        <ConnectedFleet />
      </div>
    </div>
  </section>
</template>
