<script setup lang="ts">
/**
 * A screenshot shown inside the thing it actually runs on — a wall-mounted flat panel, or a
 * portrait totem standing on the floor. The section it sits in claims "any screen", and two
 * shapes of hardware say that faster than a caption does.
 *
 * Drawn in CSS rather than shipped as an image, so it stays sharp at any size and the screen
 * inside stays the real screenshot rather than a flattened composite.
 */
withDefaults(defineProps<{ src: string; alt: string; kind?: 'tv' | 'totem' }>(), { kind: 'tv' })
</script>

<template>
  <figure class="flex flex-col items-center">
    <!-- The panel and the light it throws. The glow is a sibling of the bezel inside this
         wrapper, not a child of it: as a child it would paint behind the section's own
         background and never be seen. -->
    <div class="relative flex w-full justify-center">
      <span
        class="pointer-events-none absolute inset-0 scale-110 rounded-[28px] blur-2xl
               bg-[radial-gradient(55%_55%_at_50%_50%,rgba(130,195,255,0.4),transparent_72%)]"
        aria-hidden="true"
      />
      <div
        class="relative rounded-[14px] bg-gradient-to-b from-[#2b2f36] to-[#111317] ring-1 ring-white/15
               shadow-[0_30px_70px_-20px_rgba(0,0,0,0.65)]"
        :class="kind === 'tv' ? 'w-full p-[1.6%] pb-[2.4%]' : 'w-[62%] p-[2.2%] pb-[4%]'"
      >
        <div class="relative overflow-hidden rounded-[6px] bg-black">
          <img :src="src" :alt="alt" class="block w-full" loading="lazy" decoding="async" />
          <!-- A glare raked across the glass, so it reads as a lit display rather than a
               pasted rectangle. -->
          <span
            class="pointer-events-none absolute inset-0 bg-[linear-gradient(105deg,rgba(255,255,255,0.14)_0%,rgba(255,255,255,0.04)_18%,transparent_42%)]"
            aria-hidden="true"
          />
        </div>
        <!-- The maker's dot, the one detail every panel has. -->
        <span class="absolute inset-x-0 bottom-[0.7%] mx-auto size-[3px] rounded-full bg-white/25" aria-hidden="true" />
      </div>
    </div>

    <!-- A wall panel needs only a token stand; a totem stands on the floor. -->
    <template v-if="kind === 'tv'">
      <div class="h-6 w-[14%] bg-gradient-to-b from-[#20242a] to-[#15181c] [clip-path:polygon(22%_0,78%_0,100%_100%,0_100%)]" aria-hidden="true" />
      <div class="h-[6px] w-[34%] rounded-b-md rounded-t-sm bg-gradient-to-b from-[#2b2f36] to-[#15181c]" aria-hidden="true" />
    </template>
    <template v-else>
      <div class="h-8 w-[10%] bg-gradient-to-b from-[#20242a] to-[#15181c]" aria-hidden="true" />
      <div class="h-[10px] w-[46%] rounded-[3px] bg-gradient-to-b from-[#2b2f36] to-[#101215]" aria-hidden="true" />
    </template>

    <figcaption v-if="$slots.default" class="mt-4 text-center text-[13px] text-white/60">
      <slot />
    </figcaption>
  </figure>
</template>
