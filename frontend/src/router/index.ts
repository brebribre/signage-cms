import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    // There is no public signup — accounts are issued by a platform admin. Kept as a redirect
    // so an old link still lands somewhere sensible.
    { path: '/signup', redirect: { name: 'login' } },
    {
      path: '/',
      component: () => import('@/views/SidebarView.vue'),
      children: [
        // Overview is home: where signing in lands, and where an address with no page goes.
        { path: '', redirect: { name: 'now' } },
        {
          path: 'now',
          name: 'now',
          component: () => import('@/containers/NowContainer.vue'),
        },
        // Live Control: every screen and what it plays; open one to put a scene on it by hand.
        {
          path: 'live',
          name: 'live',
          component: () => import('@/containers/LiveControlContainer.vue'),
        },
        {
          path: 'live/:id',
          name: 'live-device',
          component: () => import('@/containers/LiveDeviceContainer.vue'),
          meta: { keyByPath: true },
        },
        {
          path: 'deploy',
          name: 'deploy',
          component: () => import('@/containers/DeployContainer.vue'),
          // Same component as campaign-detail — keyed by path so moving between creating and
          // editing (or between two campaigns) remounts it instead of carrying state across.
          meta: { keyByPath: true },
        },
        {
          path: 'media',
          name: 'media',
          component: () => import('@/containers/MediaLibraryContainer.vue'),
        },
        {
          path: 'media/:id',
          name: 'media-detail',
          component: () => import('@/containers/MediaDetailContainer.vue'),
        },
        {
          path: 'playlists',
          name: 'playlists',
          component: () => import('@/containers/PlaylistListContainer.vue'),
        },
        {
          path: 'playlists/:id',
          name: 'playlist-detail',
          component: () => import('@/containers/PlaylistEditorContainer.vue'),
        },
        {
          // Health's figures live on Now; kept as a redirect so old links still land.
          path: 'health',
          name: 'health',
          redirect: { name: 'now' },
        },
        {
          path: 'campaigns',
          name: 'campaigns',
          component: () => import('@/containers/CampaignListContainer.vue'),
        },
        {
          // A manager's screen-changing saves wait here for the owner; a manager sees their own.
          path: 'reviews',
          name: 'reviews',
          component: () => import('@/containers/ReviewsContainer.vue'),
        },
        {
          path: 'reviews/:id',
          name: 'review-detail',
          component: () => import('@/containers/ReviewDetailContainer.vue'),
          meta: { keyByPath: true },
        },
        {
          // Creating a campaign *is* the deploy flow — kept as a redirect so old links still land.
          path: 'campaigns/new',
          name: 'campaign-new',
          redirect: { name: 'deploy' },
        },
        {
          path: 'campaigns/:id',
          name: 'campaign-detail',
          component: () => import('@/containers/DeployContainer.vue'),
          meta: { keyByPath: true },
        },
        // "Screens" to the people using the CMS; still "devices" in the code and the API.
        {
          path: 'screens',
          name: 'devices',
          component: () => import('@/containers/DeviceListContainer.vue'),
        },
        {
          path: 'screens/:id',
          name: 'device-detail',
          component: () => import('@/containers/DeviceDetailContainer.vue'),
        },
        // Old addresses, from before the rename — bookmarks and shared links still land.
        { path: 'devices', redirect: { name: 'devices' } },
        { path: 'devices/:id', redirect: (to) => ({ name: 'device-detail', params: { id: to.params.id } }) },
        // One Settings page whose sections are tabs, each its own route — see SettingsContainer.
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/containers/SettingsContainer.vue'),
          // Open to everyone for General, where Log out lives; the other tabs are owner-only.
          redirect: { name: 'settings-general' },
          children: [
            {
              path: 'general',
              name: 'settings-general',
              component: () => import('@/containers/GeneralSettingsContainer.vue'),
            },
            {
              path: 'users',
              name: 'settings-users',
              component: () => import('@/containers/UserListContainer.vue'),
              meta: { ownerOnly: true },
            },
            {
              // What the account may use: screens and storage against their limits.
              path: 'limits',
              name: 'settings-limits',
              component: () => import('@/containers/LimitsContainer.vue'),
            },
          ],
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'now' } },
  ],
})

/**
 * Auth is enforced once, here — not per container.
 *
 * The guard resolves the current user by calling /me on first load, so a reload lands on
 * the right page instead of flashing the login screen.
 */
router.beforeEach(async (to) => {
  const { resolve, isSignedIn, isOwner } = useAuth()
  await resolve()

  if (!to.meta.public && !isSignedIn.value) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  // Already signed in: the sign-in page has nothing to offer, so go where signing in would
  // have taken you.
  if (to.meta.public && isSignedIn.value) {
    return { name: 'now' }
  }
  // Hiding the nav entry is a courtesy; this is the client-side half of the enforcement,
  // and the server refuses these routes regardless.
  if (to.meta.ownerOnly && !isOwner.value) {
    return { name: 'now' }
  }
  return true
})

export default router
