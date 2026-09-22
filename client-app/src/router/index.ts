import { createRouter, createWebHistory } from 'vue-router';
import { routes } from 'vue-router/auto-routes';
import { useAuthStore } from '@/stores/auth';

const rootRedirect = {
  path: '/',
  redirect: '/dashboard/default'
};

const notFoundRoute = {
  path: '/:pathMatch(.*)*',
  name: 'NotFound',
  component: () => import('@/pages/maintenance/error.vue'),
  meta: { requiresAuth: false }
};

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [rootRedirect, ...routes, notFoundRoute]
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe();
    } catch {
      // fetchMe clears invalid tokens
    }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      path: '/authentication/login',
      query: { redirect: to.fullPath }
    };
  }

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return '/dashboard/default';
  }
});
