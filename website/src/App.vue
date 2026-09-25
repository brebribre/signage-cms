<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'
import SiteFaq from '@/components/SiteFaq.vue'
import SiteFeatures from '@/components/SiteFeatures.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import SiteHero from '@/components/SiteHero.vue'
import SiteHow from '@/components/SiteHow.vue'
import SiteNav from '@/components/SiteNav.vue'
import SitePlans from '@/components/SitePlans.vue'
import SitePlatforms from '@/components/SitePlatforms.vue'
import SiteVenues from '@/components/SiteVenues.vue'

useReveal()
</script>

<template>
  <SiteNav />
  <main>
    <SiteHero />
    <SiteVenues />
    <SiteFeatures />
    <SitePlatforms />
    <SiteHow />
    <SitePlans />
    <SiteFaq />
  </main>
  <SiteFooter />
</template>
