<script setup lang="ts">
import { computed } from 'vue'
import ContactForm from './ContactForm.vue'
import LocaleSwitch from './LocaleSwitch.vue'
import wordmark from '@/assets/marien-wordmark.png'
import { homeSection } from '@/composables/usePage'
import { useI18n } from '@/i18n'

const year = new Date().getFullYear()
const { m } = useI18n()
/** Three short columns: the site, the things a customer opens once they have an account, and the
 *  account itself. Links off the site open where they are, like the header's Sign in. */
const GROUPS = computed(() => {
  const l = m.value.footer.links
  return [
    { title: m.value.footer.groups.product, links: [
      { href: '/features', label: l.features },
      { href: '/software', label: l.software },
      { href: '/demo', label: l.demo },
      { href: homeSection('uses'), label: l.uses },
    ] },
    { title: m.value.footer.groups.resources, links: [
      { href: 'https://docs.marien.co.id', label: l.docs },
      { href: 'https://api.marien.co.id/player/download', label: l.android },
      { href: 'https://player.marien.co.id', label: l.web },
    ] },
    { title: m.value.footer.groups.account, links: [
      { href: 'https://app.marien.co.id', label: l.signIn },
      { href: homeSection('contact'), label: l.requestAccess },
    ] },
  ]
})
</script>

<template>
  <!-- The closing card: the same pastel rounded shape as the features, with the ask in it:
       the Request access form, which every Request access button scrolls to. -->
  <section id="contact" class="mx-auto max-w-7xl px-5 pb-10 sm:px-8">
    <div class="reveal relative overflow-hidden rounded-xl bg-sky px-6 py-16 text-center sm:rounded-2xl sm:py-24">
      <div class="hero-ring pointer-events-none absolute -bottom-48 left-1/2 h-96 w-[48rem] -translate-x-1/2 rounded-full" aria-hidden="true" />
      <div class="hero-ring pointer-events-none absolute -bottom-72 left-1/2 h-[36rem] w-[64rem] -translate-x-1/2 rounded-full" aria-hidden="true" />
      <!-- The name as the logo itself, set on the line like a word: the wordmark's letters are
           about as tall as the heading's capitals, and sit a sixth of the image above its foot,
           so it drops by that much to put them on the text's baseline. -->
      <h2 class="relative mx-auto max-w-2xl text-4xl leading-[1.1] sm:text-6xl">
        {{ m.footer.title }}
        <img :src="wordmark" alt="Marien" class="ml-[0.1em] inline-block h-[0.95em] w-auto translate-y-[0.16em] align-baseline" />
      </h2>
      <p class="relative mx-auto mt-5 max-w-xl text-lg text-ink-muted">
        {{ m.footer.body }}
      </p>
      <ContactForm />
    </div>
  </section>
  <footer class="border-t border-line">
    <div class="mx-auto max-w-7xl px-5 pt-12 pb-8 sm:px-8">
      <div class="grid grid-cols-3 gap-x-6 gap-y-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div class="col-span-3 md:col-span-1">
          <img :src="wordmark" alt="Marien" class="h-6 w-auto" />
          <p class="mt-4 max-w-xs text-sm leading-relaxed text-ink-muted">{{ m.footer.tagline }}</p>
        </div>
        <div v-for="g in GROUPS" :key="g.title">
          <p class="text-xs font-semibold uppercase tracking-wider text-ink-subtle">{{ g.title }}</p>
          <ul class="mt-4 space-y-2.5 text-sm">
            <li v-for="l in g.links" :key="l.href">
              <a :href="l.href" class="text-ink-muted transition-colors hover:text-ink">{{ l.label }}</a>
            </li>
          </ul>
        </div>
      </div>
      <div class="mt-12 flex flex-col-reverse gap-4 border-t border-line pt-6 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p class="text-ink-subtle">© {{ year }} Marien · marien.co.id</p>
        <LocaleSwitch class="self-start sm:self-auto" />
      </div>
    </div>
  </footer>
</template>
