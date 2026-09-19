<script setup lang="ts">
/**
 * The fleet, drawn: three screens up top, each playing something, wired by dashed lines down
 * into the CMS that drives them. It replaces a paragraph about how the pieces fit together
 * with a picture of them fitting together.
 *
 * The connectors are one SVG behind the cards rather than borders on them, so the lines meet
 * at a hub and stay put whatever the cards do.
 */
const SCREENS = [
  { src: '/shots/screen-lobby.webp', name: 'Lobby TV', kind: 'Android box' },
  { src: '/shots/screen-totem.webp', name: 'Entrance totem', kind: 'Smart TV' },
  { src: '/shots/screen-cafe.webp', name: 'Cafe screen', kind: 'Browser' },
]
</script>

<template>
  <div class="relative">
    <!-- The screens. -->
    <ul class="relative z-10 grid grid-cols-3 gap-3 sm:gap-6">
      <li v-for="s in SCREENS" :key="s.name" class="rounded-2xl border border-white/12 bg-white/6 p-2.5 backdrop-blur sm:p-3">
        <!-- Every screen gets the same height and keeps its own shape, so a portrait totem sits
             beside a wall panel without towering over it. -->
        <div class="flex h-20 items-center justify-center overflow-hidden rounded-lg sm:h-28">
          <img
            :src="s.src" :alt="`${s.name} playing`"
            class="h-full w-auto rounded-md object-cover"
            loading="lazy" decoding="async"
          />
        </div>
        <p class="mt-2.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-white/55 sm:text-[11px]">
          <span class="size-1.5 shrink-0 rounded-full bg-emerald-400" /> Connected
        </p>
        <p class="text-sm text-white sm:text-base">{{ s.name }}</p>
        <p class="text-[11px] text-white/50 sm:text-xs">{{ s.kind }}</p>
      </li>
    </ul>

    <!-- The wiring: three drops to a shared rail, then one line into the CMS. -->
    <svg class="h-16 w-full sm:h-20" viewBox="0 0 300 80" preserveAspectRatio="none" aria-hidden="true">
      <g fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="1" stroke-dasharray="4 4">
        <path d="M50 0 V34" /><path d="M150 0 V34" /><path d="M250 0 V34" />
        <path d="M50 34 H250" />
        <path d="M150 34 V80" />
      </g>
      <circle cx="50" cy="34" r="2.5" fill="rgba(255,255,255,0.6)" />
      <circle cx="150" cy="34" r="2.5" fill="rgba(255,255,255,0.6)" />
      <circle cx="250" cy="34" r="2.5" fill="rgba(255,255,255,0.6)" />
    </svg>

    <!-- The CMS they all answer to. -->
    <div class="overflow-hidden rounded-2xl border border-white/12 bg-white/6 p-2.5 backdrop-blur sm:p-3">
      <img src="/shots/overview.webp" alt="The Paskall dashboard driving the screens" class="block w-full rounded-lg" loading="lazy" decoding="async" />
    </div>
  </div>
</template>
