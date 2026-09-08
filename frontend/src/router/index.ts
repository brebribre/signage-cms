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
    {
      path: '/signup',
      name: 'signup',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/views/SidebarView.vue'),
      children: [
        { path: '', redirect: { name: 'media' } },
        {
          path: 'media',
          name: 'media',
          component: () => import('@/containers/MediaLibraryContainer.vue'),
        },
        {
          path: 'playlists',
          name: 'playlists',
          component: () => import('@/containers/PlaceholderContainer.vue'),
          props: { title: 'Playlists', phase: 'Phase 7' },
        },
        {
          path: 'devices',
          name: 'devices',
          component: () => import('@/containers/PlaceholderContainer.vue'),
          props: { title: 'Devices', phase: 'Phase 9' },
        },
        {
          path: 'settings/users',
          name: 'settings-users',
          component: () => import('@/containers/PlaceholderContainer.vue'),
          props: { title: 'Users', phase: 'Phase 9b' },
          meta: { ownerOnly: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'media' } },
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
  if (to.meta.public && isSignedIn.value) {
    return { name: 'media' }
  }
  // Hiding the nav entry is a courtesy; this is the client-side half of the enforcement,
  // and the server refuses these routes regardless.
  if (to.meta.ownerOnly && !isOwner.value) {
    return { name: 'media' }
  }
  return true
})

export default router
