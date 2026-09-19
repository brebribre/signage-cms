<script setup lang="ts">
/**
 * The screen in the hero, drawn flat: a portrait totem with its glass, its bezel and a base.
 * What it plays comes from the CMS panel beside it, so the two together are the product's
 * whole loop in one gesture.
 *
 * Plain markup rather than a 3D scene. The picture a visitor needs is "this is a screen and it
 * changed", and that costs a couple of gradients here instead of half a megabyte of renderer
 * and a model to feed it.
 *
 * The dark bezel between the pale chassis and the glass is what makes it read as a screen: a
 * slide in the brand blues, on a blue band, needs something black around it or it is just a
 * rectangle of the background.
 */
import { SLIDES } from '@/data/slides'

defineProps<{ active: number }>()
</script>

<template>
  <div class="w-60 sm:w-[17rem] lg:w-[19rem]">
    <!-- The chassis. -->
    <div class="rounded-[1.7rem] bg-gradient-to-b from-[#dcecfb] via-[#a9cbeb] to-[#7ba2c7] p-2.5 shadow-[0_40px_80px_-28px_rgba(0,12,40,0.7)] ring-1 ring-white/40">
      <!-- The bezel. -->
      <div class="rounded-[1.15rem] bg-[#0a1526] p-2 shadow-[inset_0_1px_2px_rgba(255,255,255,0.18)]">
        <div class="relative aspect-[9/16] overflow-hidden rounded-[0.7rem] bg-[#07132b]">
          <div
            v-for="(s, i) in SLIDES" :key="s.name"
            class="absolute inset-0 transition-opacity duration-500"
            :class="active === i ? 'opacity-100' : 'opacity-0'"
            :aria-hidden="active !== i"
          >
            <img
              v-if="s.src" :src="s.src" :alt="s.title"
              class="size-full object-cover" loading="lazy" decoding="async"
            />
            <div v-else class="size-full" :style="{ background: `linear-gradient(160deg, ${s.from}, ${s.to})` }" />
            <!-- The words, centred and over a scrim, so they hold on any picture and stay clear
                 of whatever overlaps the screen's corners. -->
            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/35 to-transparent px-4 pb-7 pt-12 text-center">
              <p class="display text-xl leading-tight text-white lg:text-2xl">{{ s.title }}</p>
              <p class="mt-1 text-[13px] text-white/75">{{ s.sub }}</p>
            </div>
          </div>
          <!-- Glass: one soft highlight across the top left. -->
          <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/12 via-white/0 to-white/0" aria-hidden="true" />
        </div>
      </div>
    </div>

    <!-- The stand. -->
    <div class="mx-auto h-3.5 w-[42%] bg-gradient-to-b from-[#9dbfde] to-[#83a5c3]" aria-hidden="true" />
    <div class="mx-auto h-4 w-[78%] rounded-b-2xl bg-gradient-to-b from-[#b2cde7] to-[#7295b4] shadow-[0_18px_30px_-16px_rgba(0,12,40,0.85)]" aria-hidden="true" />
  </div>
</template>
