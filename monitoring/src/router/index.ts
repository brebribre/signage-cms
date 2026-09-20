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
      path: '/',
      component: () => import('@/views/ShellView.vue'),
      children: [
        { path: '', redirect: { name: 'accounts' } },
        {
          path: 'accounts',
          name: 'accounts',
          component: () => import('@/containers/AccountsContainer.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'accounts' } },
  ],
})

/**
 * Auth is enforced once, here. "Signed in" means /admin/me answered 200, which it only does
 * for a platform admin — so this one check is also the admin check. The server refuses
 * every /admin/* call regardless; this just keeps a customer from seeing an empty shell.
 */
router.beforeEach(async (to) => {
  const { resolve, isSignedIn } = useAuth()
  await resolve()

  if (!to.meta.public && !isSignedIn.value) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.meta.public && isSignedIn.value) {
    return { name: 'accounts' }
  }
  return true
})

export default router
