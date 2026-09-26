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
         picture leaves open, beside the title rather than under it. It fades out toward the
         left, so a big pattern never sits under the words. -->
    <div class="@container pointer-events-none absolute inset-0 [mask-image:linear-gradient(105deg,transparent_30%,#000_72%)]" aria-hidden="true">
      <div v-if="pattern === 'sweep'" class="card-sweep absolute -right-[35%] left-[15%] top-[12%] h-[56%] -rotate-[22deg] rounded-[50%]" />
      <div v-else-if="pattern === 'rise'" class="card-sweep absolute -right-[40%] left-[22%] -top-[16%] h-[54%] rotate-[24deg] rounded-[50%]" />
      <div v-else-if="pattern === 'bloom'" class="card-bloom absolute -right-[25%] -top-[32%] aspect-square w-[92%] rounded-full" />
      <template v-else-if="pattern === 'twin'">
        <div class="card-sweep absolute -right-[25%] left-[40%] -top-[4%] h-[25%] -rotate-[40deg] rounded-[50%]" />
        <div class="card-sweep absolute -right-[40%] left-[58%] top-[22%] h-[20%] -rotate-[40deg] rounded-[50%] opacity-80" />
      </template>
      <template v-else>
        <div class="hero-dome absolute -right-[40%] -top-[55%] aspect-square w-[115%] rotate-180 rounded-t-full" />
        <div class="hero-ring absolute -right-[35%] -top-[62%] aspect-square w-[100%] rounded-full" />
        <div class="hero-ring absolute -right-[50%] -top-[80%] aspect-square w-[132%] rounded-full" />
        <div class="card-bloom absolute -right-[14%] -top-[20%] aspect-square w-[55%] rounded-full opacity-75" />
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
