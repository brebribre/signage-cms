<script setup lang="ts">
import { ref } from 'vue'
import IconAdd from '~icons/material-symbols/add'

import { useI18n } from '@/i18n'

const { m } = useI18n()
const open = ref<number | null>(0)
</script>

<template>
  <section id="faq" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="grid gap-10 lg:grid-cols-12">
      <div class="reveal lg:col-span-5">
        <h2 class="text-4xl leading-[1.1] sm:text-5xl">{{ m.faq.title }}</h2>
        <p class="mt-5 text-ink-muted">{{ m.faq.more }} <a href="#contact" class="text-brand underline underline-offset-4">{{ m.faq.write }}</a>.</p>
      </div>
      <ul class="reveal flex flex-col gap-3 lg:col-span-7">
        <li v-for="(item, i) in m.faq.items" :key="i" class="rounded-xl transition-colors" :class="open === i ? 'bg-tint' : 'bg-surface ring-1 ring-line'">
          <button type="button" class="flex w-full items-center justify-between gap-4 px-6 py-5 text-left" :aria-expanded="open === i" @click="open = open === i ? null : i">
            <span class="display text-lg text-ink">{{ item.q }}</span>
            <span class="flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors" :class="open === i ? 'bg-brand-deep text-white' : 'bg-white text-ink ring-1 ring-line'">
              <IconAdd class="size-5 transition-transform" :class="open === i && 'rotate-45'" />
            </span>
          </button>
          <p v-if="open === i" class="px-6 pb-6 text-sm leading-relaxed text-ink-muted">{{ item.a }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
