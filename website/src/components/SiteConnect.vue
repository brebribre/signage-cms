<script setup lang="ts">
/** Connecting a screen: the pairing code a new player shows, and the same code typed into the
 *  CMS on a phone — which is all it takes. */
import FeatureCard from './FeatureCard.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="connect">
    <FeatureCard>
      <template #visual>
        <!-- The one stat, then the two halves of pairing: the TV showing its code, and the phone
             it is typed into, overlapping the TV and running off the card's bottom-right corner.
             Sized in container units, so the pair keeps its shape from a phone to the
             three-column page; in the narrow, tall column of the wide page they grow to fill it. Real screenshots: the web player's pairing screen and the CMS's
             Connect a screen form, with the same code. -->
        <div class="relative">
          <div class="relative z-10 w-36 rounded-xl bg-sky-strong p-4 shadow-[0_20px_40px_-24px_rgba(0,24,77,0.5)] sm:w-40 sm:p-5">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-brand-deep/70">{{ m.connect.statUnder }}</p>
            <p class="display text-4xl text-brand-deep">{{ m.connect.statValue }}</p>
            <p class="mt-0.5 text-xs leading-snug text-brand-deep/80">{{ m.connect.statCaption }}</p>
          </div>

          <div class="relative mt-5 h-[70cqw] lg:h-[100cqw]">
            <!-- The TV -->
            <div class="absolute left-0 top-[6cqw] w-[76cqw] lg:top-[34cqw] lg:w-[80cqw]">
              <div class="rounded-[2.4cqw] bg-[#0f1115] p-[1.3cqw] shadow-[0_30px_60px_-30px_rgba(0,20,120,0.5)]">
                <img
                  src="/shots/connect-tv.webp" :alt="m.connect.photoAlt"
                  class="block aspect-video w-full rounded-[1.1cqw]"
                  loading="lazy" decoding="async"
                />
              </div>
              <div class="mx-auto h-[1.5cqw] w-[24cqw] rounded-b-[1.2cqw] bg-[#0f1115]" aria-hidden="true" />
            </div>

            <!-- The phone, the code typed in -->
            <div class="absolute -right-[3cqw] top-0 w-[34cqw] lg:-right-[10cqw] lg:w-[46cqw] rounded-[5.2cqw] bg-[#0f1115] p-[1.1cqw] shadow-[0_40px_80px_-40px_rgba(0,20,120,0.6)]" aria-hidden="true">
              <div class="relative overflow-hidden rounded-[4.2cqw]">
                <span class="absolute left-1/2 top-[1.8cqw] z-10 h-[2.4cqw] w-[10cqw] -translate-x-1/2 rounded-full bg-[#0f1115]" />
                <img src="/shots/connect-phone.webp" alt="" class="block aspect-[1170/2532] w-full" loading="lazy" decoding="async" />
              </div>
            </div>
          </div>
        </div>
      </template>

      <h3 class="text-xl leading-[1.2] sm:text-4xl sm:leading-[1.1]">{{ m.connect.title }}</h3>
      <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ m.connect.body }}</p>
    </FeatureCard>
  </section>
</template>
