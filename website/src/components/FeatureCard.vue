<script setup lang="ts">
/**
 * One of the feature cards, in a pale brand tint so it stands off the white page, laid out the
 * way a product page's bento is: the title and a line at the top, and the thing itself below,
 * standing on a sweep of the brand blues and running off the card's right and bottom edges, as
 * if the card were a window onto a bigger scene.
 * The card fills its grid cell, and the picture keeps to the foot however tall that is.
 */
</script>

<template>
  <article class="relative flex h-full flex-col overflow-hidden rounded-[2rem] bg-brand-soft ring-1 ring-tint-strong/60">
    <div class="relative p-6 sm:p-8 lg:p-10">
      <slot />
    </div>
    <div class="@container relative mt-auto min-w-0 pl-6 sm:pl-8 lg:pl-10">
      <!-- The sweep, behind the picture. -->
      <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[6%] h-[86%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
      <div class="relative">
        <slot name="visual" />
      </div>
    </div>
  </article>
</template>
