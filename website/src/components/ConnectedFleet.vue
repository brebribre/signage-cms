<script setup lang="ts">
/**
 * The fleet, drawn: three screens up top, each playing something, wired by dashed lines down
 * into the CMS that drives them. It replaces a paragraph about how the pieces fit together
 * with a picture of them fitting together.
 *
 * The connectors are one SVG between the cards rather than borders on them, so the lines meet
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
      <li
        v-for="s in SCREENS" :key="s.name"
        class="rounded-2xl border border-line bg-canvas p-2.5 shadow-[0_20px_50px_-30px_rgba(0,24,77,0.45)] sm:p-3"
      >
        <!-- Every screen gets the same height and keeps its own shape, so a portrait totem sits
             beside a wall panel without towering over it. -->
        <div class="flex h-20 items-center justify-center overflow-hidden rounded-lg bg-page sm:h-28">
          <img
            :src="s.src" :alt="`${s.name} playing`"
            class="h-full w-auto rounded-md object-cover"
            loading="lazy" decoding="async"
          />
        </div>
        <p class="mt-2.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-ink-subtle sm:text-[11px]">
          <span class="size-1.5 shrink-0 rounded-full bg-emerald-500" /> Connected
        </p>
        <p class="truncate text-sm text-ink sm:text-base">{{ s.name }}</p>
        <p class="text-[11px] text-ink-subtle sm:text-xs">{{ s.kind }}</p>
      </li>
    </ul>

    <!-- The wiring: three drops to a shared rail, then one line into the CMS. -->
    <svg class="h-16 w-full sm:h-20" viewBox="0 0 300 80" preserveAspectRatio="none" aria-hidden="true">
      <g fill="none" stroke="rgba(0,51,153,0.28)" stroke-width="1" stroke-dasharray="4 4">
        <path d="M50 0 V34" /><path d="M150 0 V34" /><path d="M250 0 V34" />
        <path d="M50 34 H250" />
        <path d="M150 34 V80" />
      </g>
      <circle cx="50" cy="34" r="2.5" fill="rgba(0,51,153,0.45)" />
      <circle cx="150" cy="34" r="2.5" fill="rgba(0,51,153,0.45)" />
      <circle cx="250" cy="34" r="2.5" fill="rgba(0,51,153,0.45)" />
    </svg>

    <!-- The CMS they all answer to. -->
    <div class="overflow-hidden rounded-2xl border border-line bg-canvas p-2.5 shadow-[0_30px_80px_-40px_rgba(0,24,77,0.5)] sm:p-3">
      <!-- Cropped to the top of the page: the empty run below the list is real, and dull. -->
      <div class="aspect-[2.1] overflow-hidden rounded-lg">
        <img
          src="/shots/overview.webp" alt="The Paskall dashboard driving the screens"
          class="block w-full object-cover object-top" loading="lazy" decoding="async"
        />
      </div>
    </div>
  </div>
</template>
