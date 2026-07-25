import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/public/HomeView.vue'
import AccountView from '../views/dashboard/AccountView.vue'
import BillingStandardsView from '../views/dashboard/BillingStandardsView.vue'
import CreditLedgerView from '../views/dashboard/CreditLedgerView.vue'
import DashboardLayout from '../layouts/DashboardLayout.vue'
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'
import WorkspaceCanvasView from '../views/canvas/WorkspaceCanvasView.vue'
import WorkspaceHome from '../views/dashboard/WorkspaceHome.vue'

export function createAppRouter(authStore) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'home', component: HomeView, meta: { guestOnly: true } },
      { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
      { path: '/register', name: 'register', component: RegisterView, meta: { guestOnly: true } },
      {
        path: '/dashboard',
        component: DashboardLayout,
        redirect: { name: 'workspaces' },
        meta: { requiresAuth: true },
        children: [
          { path: 'workspaces', name: 'workspaces', component: WorkspaceHome, meta: { navKey: 'workspaces' } },
          { path: 'account', name: 'account', component: AccountView, meta: { navKey: 'overview' } },
          { path: 'credits', name: 'credits', component: CreditLedgerView, meta: { navKey: 'credits' } },
          { path: 'pricing', name: 'pricing', component: BillingStandardsView, meta: { navKey: 'pricing' } },
        ],
      },
      { path: '/canvas/:workspaceId', name: 'canvas', component: WorkspaceCanvasView, meta: { requiresAuth: true } },
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
