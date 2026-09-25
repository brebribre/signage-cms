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
  <section id="plans" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="reveal text-center">
      <span class="tag text-brand-deep">Pricing</span>
      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Priced per screen</h2>
      <p class="mt-5 text-lg text-ink-muted">Pay for screens, never for storage.</p>
    </div>
    <ul class="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <li
        v-for="p in PLANS" :key="p.name"
        class="reveal flex flex-col rounded-3xl p-7"
        :class="p.featured ? 'bg-brand-deep text-white' : 'bg-tint/60 ring-1 ring-tint-strong/60'"
      >
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-lg">{{ p.name }}</h3>
          <span v-if="p.featured" class="rounded-full bg-accent px-2.5 py-0.5 text-[11px] font-semibold text-brand-deep">Popular</span>
        </div>
        <p class="display mt-3 text-3xl">{{ p.price }}</p>
        <p class="mt-1 text-sm" :class="p.featured ? 'text-white/70' : 'text-ink-muted'">{{ p.blurb }}</p>
        <ul class="mt-6 mb-8 flex flex-col gap-2.5 text-sm">
          <li v-for="pt in p.points" :key="pt" class="flex items-start gap-2">
            <IconCheck class="mt-0.5 size-4 shrink-0" :class="p.featured ? 'text-accent' : 'text-brand'" /> {{ pt }}
          </li>
        </ul>
        <a
          href="#contact" class="mt-auto inline-flex justify-center rounded-full px-4 py-2.5 text-sm font-medium transition-colors"
          :class="p.featured ? 'bg-white text-brand-deep hover:bg-sky' : 'bg-brand-deep text-white hover:bg-brand'"
        >Talk to us</a>
      </li>
    </ul>
  </section>
</template>
