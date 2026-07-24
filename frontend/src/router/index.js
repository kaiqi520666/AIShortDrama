import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import AccountView from '../views/AccountView.vue'
import BillingStandardsView from '../views/BillingStandardsView.vue'
import CreditLedgerView from '../views/CreditLedgerView.vue'
import DashboardLayout from '../components/dashboard/DashboardLayout.vue'
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
