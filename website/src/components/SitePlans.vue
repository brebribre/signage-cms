<script setup lang="ts">
import IconCheck from '~icons/material-symbols/check'

const PLANS = [
  { name: 'Free', price: 'Free', blurb: 'Try it on one screen.', points: ['1 screen', '1 GB of media', 'Owner only', 'Every content feature'] },
  { name: 'Standard', price: 'Per screen', blurb: 'For a shop, a lobby, a clinic.', points: ['Unlimited media', 'Up to 5 users', 'Schedules and campaigns', 'Multi-element scenes'], featured: true },
  { name: 'Pro', price: 'Per screen', blurb: 'For teams that hand work to managers.', points: ['Unlimited users', 'Reviews and approvals', 'Power schedules and remote control', 'Proof of play'] },
  { name: 'Enterprise', price: 'Let’s talk', blurb: 'For many venues.', points: ['Everything in Pro', 'Volume pricing', 'Onboarding help', 'Single sign-on, on request'] },
]
</script>

<template>
  <section id="plans" class="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="reveal max-w-2xl">
      <p class="text-[13px] uppercase tracking-wider text-brand">Plans</p>
      <h2 class="mt-3 text-3xl sm:text-4xl">Priced per screen, like the screens are.</h2>
      <p class="mt-4 text-ink-muted">Accounts are set up by us today, so every plan starts with a conversation. The shape is the same across the board: pay for screens, never for storage.</p>
    </div>
    <ul class="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <li
        v-for="p in PLANS" :key="p.name"
        class="reveal flex flex-col rounded-2xl border p-6"
        :class="p.featured ? 'border-brand bg-brand-soft/40' : 'border-line bg-canvas'"
      >
        <h3 class="text-lg">{{ p.name }}</h3>
        <p class="display mt-1 text-2xl">{{ p.price }}</p>
        <p class="mt-1 text-sm text-ink-muted">{{ p.blurb }}</p>
        <ul class="mt-5 mb-6 flex flex-col gap-2 text-sm">
          <li v-for="pt in p.points" :key="pt" class="flex items-start gap-2">
            <IconCheck class="mt-0.5 size-4 shrink-0 text-brand" /> {{ pt }}
          </li>
        </ul>
        <a href="#contact" class="mt-auto inline-flex justify-center rounded-full px-4 py-2 text-sm transition-colors" :class="p.featured ? 'bg-brand text-ink-inverse hover:bg-hover' : 'border border-line-strong text-ink hover:border-ink'">Talk to us</a>
      </li>
    </ul>
  </section>
</template>
