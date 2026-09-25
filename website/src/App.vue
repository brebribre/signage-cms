<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'
import SiteFaq from '@/components/SiteFaq.vue'
import SiteFeatures from '@/components/SiteFeatures.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import SiteHero from '@/components/SiteHero.vue'
import SiteNav from '@/components/SiteNav.vue'
import SiteResponsive from '@/components/SiteResponsive.vue'
import SiteVenues from '@/components/SiteVenues.vue'

useReveal()
</script>

<template>
  <SiteNav />
  <main>
    <SiteHero />
    <SiteVenues />
    <SiteFeatures />
    <SiteResponsive />
    <SiteFaq />
  </main>
  <SiteFooter />
</template>
