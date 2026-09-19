<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'
import SiteConnect from '@/components/SiteConnect.vue'
import SiteDesign from '@/components/SiteDesign.vue'
import SiteFaq from '@/components/SiteFaq.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import SiteHero from '@/components/SiteHero.vue'
import SiteHow from '@/components/SiteHow.vue'
import SiteNav from '@/components/SiteNav.vue'
import SitePlans from '@/components/SitePlans.vue'
import SitePublish from '@/components/SitePublish.vue'

useReveal()
</script>

<template>
  <SiteNav />
  <main>
    <SiteHero />
    <SiteConnect />
    <SiteDesign />
    <SitePublish />
    <SiteHow />
    <SitePlans />
    <SiteFaq />
  </main>
  <SiteFooter />
</template>
