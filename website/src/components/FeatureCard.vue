<script setup lang="ts">
/**
 * One of the feature cards, in a pale brand tint so it stands off the white page, laid out the
 * way a product page's bento is: the title and a line at the top, and the thing itself below,
 * standing on a pattern of the brand blues and running off the card's right and bottom edges, as
 * if the card were a window onto a bigger scene.
 * The card fills its grid cell, and the picture keeps to the foot however tall that is.
 *
 * Each card picks its own pattern, all from the same blues, so a row of them reads as a family
 * rather than one background repeated: a diagonal sweep, the same band rising the other way, a
 * soft bloom in the corner, two thin steep bands, or the hero's dome with its rings.
 */
export type CardPattern = 'sweep' | 'rise' | 'bloom' | 'twin' | 'arc'
withDefaults(defineProps<{ pattern?: CardPattern }>(), { pattern: 'sweep' })
</script>

<template>
  <article class="relative flex h-full flex-col overflow-hidden rounded-2xl bg-brand-soft ring-1 ring-tint-strong/60">
    <!-- The pattern, behind everything, weighted to the top right: the part of the card the
         picture leaves open, beside the title rather than under it. -->
    <div class="@container pointer-events-none absolute inset-0" aria-hidden="true">
      <div v-if="pattern === 'sweep'" class="card-sweep absolute -right-[25%] left-[30%] top-[18%] h-[38%] -rotate-[22deg] rounded-[50%]" />
      <div v-else-if="pattern === 'rise'" class="card-sweep absolute -right-[30%] left-[40%] -top-[6%] h-[34%] rotate-[24deg] rounded-[50%]" />
      <div v-else-if="pattern === 'bloom'" class="card-bloom absolute -right-[18%] -top-[22%] aspect-square w-[62%] rounded-full" />
      <template v-else-if="pattern === 'twin'">
        <div class="card-sweep absolute -right-[20%] left-[55%] top-[2%] h-[16%] -rotate-[40deg] rounded-[50%]" />
        <div class="card-sweep absolute -right-[35%] left-[70%] top-[20%] h-[13%] -rotate-[40deg] rounded-[50%] opacity-80" />
      </template>
      <template v-else>
        <div class="hero-dome absolute -right-[30%] -top-[40%] aspect-square w-[80%] rotate-180 rounded-t-full" />
        <div class="hero-ring absolute -right-[25%] -top-[45%] aspect-square w-[70%] rounded-full" />
        <div class="hero-ring absolute -right-[35%] -top-[58%] aspect-square w-[92%] rounded-full" />
        <div class="card-bloom absolute -right-[8%] -top-[12%] aspect-square w-[34%] rounded-full opacity-75" />
      </template>
    </div>
    <div class="relative p-6 sm:p-8 lg:p-10">
      <slot />
    </div>
    <div class="@container relative mt-auto min-w-0 pl-6 sm:pl-8 lg:pl-10">
      <slot name="visual" />
    </div>
  </article>
</template>
