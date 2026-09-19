<script setup lang="ts">
const STEPS = [
  { n: '01', title: 'Connect a screen', text: 'Open the player on the box, or the web player in the TV’s browser. It shows a six-letter code. Type it into Paskall, name the screen, say how it is mounted. Under a minute.' },
  { n: '02', title: 'Build a playlist', text: 'Upload pictures and videos, add a website, write a headline. Each becomes a scene; arrange them and set how long each one stays. Preview it at the screen’s real shape.' },
  { n: '03', title: 'Deploy a campaign', text: 'Pick screens, pick the playlist or a schedule, deploy. Screens hear about it within seconds and fetch what they need. From then on they run themselves.' },
]
</script>

<template>
  <section id="how" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="reveal max-w-2xl">
      <p class="text-[13px] font-medium uppercase tracking-wider text-brand">How it works</p>
      <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">Three steps, then it is Tuesday and the screens are still right.</h2>
    </div>
    <!-- A numbered rail: the line runs through the steps, so the order is the picture. -->
    <ol class="mt-14 grid gap-10 md:grid-cols-3">
      <li v-for="s in STEPS" :key="s.n" class="reveal relative border-t border-line pt-6">
        <span class="display absolute -top-3.5 left-0 bg-canvas pr-3 text-sm tracking-widest text-brand">{{ s.n }}</span>
        <h3 class="text-lg">{{ s.title }}</h3>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ s.text }}</p>
      </li>
    </ol>
  </section>
</template>
