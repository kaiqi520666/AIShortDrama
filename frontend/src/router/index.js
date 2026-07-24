import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import AccountView from '../views/AccountView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import WorkspaceCanvasView from '../views/WorkspaceCanvasView.vue'
import WorkspaceHome from '../views/WorkspaceHome.vue'

export function createAppRouter(authStore) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'home', component: HomeView, meta: { guestOnly: true } },
      { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
      { path: '/register', name: 'register', component: RegisterView, meta: { guestOnly: true } },
      { path: '/workspaces', name: 'workspaces', component: WorkspaceHome, meta: { requiresAuth: true } },
      { path: '/workspaces/:id', name: 'canvas', component: WorkspaceCanvasView, meta: { requiresAuth: true } },
      { path: '/account', name: 'account', component: AccountView, meta: { requiresAuth: true } },
      { path: '/:pathMatch(.*)*', redirect: '/' },
    ],
  })

  router.beforeEach(async (to) => {
    await authStore.restore()
    if (to.meta.requiresAuth && !authStore.user) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.guestOnly && authStore.user) return { name: 'workspaces' }
  })
  return router
}
