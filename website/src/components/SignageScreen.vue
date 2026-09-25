<script setup lang="ts">
/**
 * The screen in the hero, drawn flat: a portrait totem with its glass, a dark bezel and a base.
 * What it plays comes from the playlist picker beside it, so the two together are the
 * product's whole loop in one gesture.
 *
 * Plain markup rather than a 3D scene. The picture a visitor needs is "this is a screen and it
 * changed", and that costs a couple of gradients here instead of half a megabyte of renderer
 * and a model to feed it. The chassis is near-black so it stands off the pale dome behind it
 * the way a phone does in a product shot.
 */
import { SLIDES } from '@/data/slides'

defineProps<{ active: number }>()
</script>

<template>
  <div class="w-56 sm:w-64 lg:w-[17rem]">
    <!-- The chassis. -->
    <div class="rounded-[1.9rem] bg-gradient-to-b from-[#2a2f3a] to-[#0b0e14] p-2.5 shadow-[0_40px_80px_-30px_rgba(0,24,77,0.55)] ring-1 ring-black/40">
      <div class="relative aspect-[9/16] overflow-hidden rounded-[1.35rem] bg-[#07132b]">
        <div
          v-for="(s, i) in SLIDES" :key="s.name"
          class="absolute inset-0 transition-opacity duration-500"
          :class="active === i ? 'opacity-100' : 'opacity-0'"
          :aria-hidden="active !== i"
        >
          <img v-if="s.src" :src="s.src" :alt="s.title" class="size-full object-cover" decoding="async" />
          <div v-else class="size-full" :style="{ background: `linear-gradient(160deg, ${s.from}, ${s.to})` }" />
          <!-- The words over a scrim, so they hold on any picture. -->
          <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/35 to-transparent px-4 pb-7 pt-12 text-center">
            <p class="display text-xl leading-tight text-white lg:text-2xl">{{ s.title }}</p>
            <p class="mt-1 text-[13px] text-white/75">{{ s.sub }}</p>
          </div>
        </div>
        <!-- Glass: one soft highlight across the top left. -->
        <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/12 via-white/0 to-white/0" aria-hidden="true" />
      </div>
    </div>

    <!-- The stand. -->
    <div class="mx-auto h-4 w-[38%] bg-gradient-to-b from-[#1b1f28] to-[#2a2f3a]" aria-hidden="true" />
    <div class="mx-auto h-3.5 w-[72%] rounded-t-md rounded-b-2xl bg-gradient-to-b from-[#2a2f3a] to-[#0b0e14]" aria-hidden="true" />
  </div>
</template>
