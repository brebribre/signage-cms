<script setup lang="ts">
const STEPS = [
  { n: '01', title: 'Connect a screen', text: 'The player shows a six letter code. Type it in. Under a minute.' },
  { n: '02', title: 'Build a playlist', text: 'Upload, arrange, add a headline. Preview at the screen’s real shape.' },
  { n: '03', title: 'Deploy a campaign', text: 'Pick screens, pick content, deploy. They run themselves from there.' },
]
</script>

<template>
  <section id="how" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <h2 class="reveal max-w-2xl text-3xl leading-tight sm:text-4xl">Up and playing in three steps.</h2>
    <!-- A numbered rail: the line runs through the steps, so the order is the picture. -->
    <ol class="mt-12 grid gap-10 md:grid-cols-3">
      <li v-for="s in STEPS" :key="s.n" class="reveal relative border-t border-line pt-6">
        <span class="display absolute -top-3.5 left-0 bg-canvas pr-3 text-sm tracking-widest text-brand">{{ s.n }}</span>
        <h3 class="text-lg">{{ s.title }}</h3>
        <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ s.text }}</p>
      </li>
    </ol>
  </section>
</template>
