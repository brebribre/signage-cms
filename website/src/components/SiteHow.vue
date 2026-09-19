<script setup lang="ts">
const STEPS = [
  { n: '1', title: 'Connect a screen', text: 'Open the player on the box or the TV’s browser. It shows a six-letter code. Type it into Paskall, name the screen, say how it is mounted. Under a minute.' },
  { n: '2', title: 'Build a playlist', text: 'Upload pictures and videos, add a website, write a headline. Each becomes a scene; arrange them, set how long each stays. Preview it on the screen’s real shape.' },
  { n: '3', title: 'Deploy a campaign', text: 'Pick screens, pick the playlist or a schedule, deploy. Screens hear about it within seconds and download what they need. From then on they run themselves.' },
]
</script>

<template>
  <section id="how" class="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="reveal max-w-2xl">
      <p class="text-[13px] uppercase tracking-wider text-brand">How it works</p>
      <h2 class="mt-3 text-3xl sm:text-4xl">Three steps, then it is Tuesday and the screens are still right.</h2>
    </div>
    <ol class="mt-12 grid gap-6 md:grid-cols-3">
      <li v-for="s in STEPS" :key="s.n" class="reveal relative rounded-2xl bg-page p-6">
        <span class="display text-5xl text-brand/20">{{ s.n }}</span>
        <h3 class="mt-2 text-lg">{{ s.title }}</h3>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ s.text }}</p>
      </li>
    </ol>
  </section>
</template>
