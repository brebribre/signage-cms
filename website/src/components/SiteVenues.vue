<script setup lang="ts">
/**
 * The strip under the hero, where a product page usually lists its customers. These are the
 * kinds of places Paskall is made for, set in a mix of type the way a logo wall is, so the
 * rhythm is there without claiming names we have no right to.
 */
const VENUES = [
  { label: 'Cafés', cls: 'font-serif italic text-2xl' },
  { label: 'LOBBIES', cls: 'display font-semibold tracking-[0.18em] text-xl' },
  { label: 'clinics', cls: 'display text-2xl font-light' },
  { label: 'Retail', cls: 'font-serif text-2xl' },
  { label: 'CAMPUSES', cls: 'font-mono text-lg tracking-widest' },
  { label: 'Restaurants', cls: 'display text-2xl font-bold tracking-tight' },
  { label: 'Hotels', cls: 'font-serif italic text-2xl font-semibold' },
  { label: 'SHOWROOMS', cls: 'display text-lg font-medium tracking-[0.3em]' },
]
</script>

<template>
  <section class="border-b border-line" aria-label="Where Paskall runs">
    <div class="mx-auto max-w-7xl overflow-hidden px-5 py-10 sm:px-8">
      <!-- Faded at both ends so the loop slides in and out rather than being cut. -->
      <div class="[mask-image:linear-gradient(90deg,transparent,#000_12%,#000_88%,transparent)]">
        <ul class="marquee flex w-max items-center gap-16 text-ink/70">
          <li v-for="(v, i) in [...VENUES, ...VENUES]" :key="i" :class="v.cls" :aria-hidden="i >= VENUES.length">
            {{ v.label }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
