import { createRouter, createWebHistory } from 'vue-router'

const HomeView = () => import('../views/public/HomeView.vue')
const AccountView = () => import('../views/dashboard/AccountView.vue')
const BillingStandardsView = () => import('../views/dashboard/BillingStandardsView.vue')
const CreditLedgerView = () => import('../views/dashboard/CreditLedgerView.vue')
const GenerationHistoryView = () => import('../views/dashboard/GenerationHistoryView.vue')
const RechargeView = () => import('../views/dashboard/RechargeView.vue')
const DashboardLayout = () => import('../layouts/DashboardLayout.vue')
const LoginView = () => import('../views/auth/LoginView.vue')
const RegisterView = () => import('../views/auth/RegisterView.vue')
const WorkspaceCanvasView = () => import('../views/canvas/WorkspaceCanvasView.vue')
const WorkspaceHome = () => import('../views/dashboard/WorkspaceHome.vue')
const AdminUsersView = () => import('../views/admin/AdminUsersView.vue')
const AdminPricingView = () => import('../views/admin/AdminPricingView.vue')
const AdminTasksView = () => import('../views/admin/AdminTasksView.vue')
const AdminAuditsView = () => import('../views/admin/AdminAuditsView.vue')
const AdminRechargeView = () => import('../views/admin/AdminRechargeView.vue')
const AdminOverviewView = () => import('../views/admin/AdminOverviewView.vue')
const AdminModelsView = () => import('../views/admin/AdminModelsView.vue')
const AdminTemplatesView = () => import('../views/admin/AdminTemplatesView.vue')
const AdminReferenceAssetsView = () => import('../views/admin/AdminReferenceAssetsView.vue')

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
          { path: 'recharge', name: 'recharge', component: RechargeView, meta: { navKey: 'recharge' } },
          { path: 'generations', name: 'generations', component: GenerationHistoryView, meta: { navKey: 'generations' } },
          { path: 'pricing', name: 'pricing', component: BillingStandardsView, meta: { navKey: 'pricing' } },
        ],
      },
      {
        path: '/admin',
        component: DashboardLayout,
        redirect: { name: 'admin-overview' },
        meta: { requiresAuth: true, requiresAdmin: true },
        children: [
          { path: 'overview', name: 'admin-overview', component: AdminOverviewView, meta: { navKey: 'admin-overview' } },
          { path: 'users', name: 'admin-users', component: AdminUsersView, meta: { navKey: 'admin-users' } },
          { path: 'models', name: 'admin-models', component: AdminModelsView, meta: { navKey: 'admin-models' } },
          { path: 'pricing', name: 'admin-pricing', component: AdminPricingView, meta: { navKey: 'admin-pricing' } },
          { path: 'templates', name: 'admin-templates', component: AdminTemplatesView, meta: { navKey: 'admin-templates' } },
          { path: 'reference-assets', name: 'admin-reference-assets', component: AdminReferenceAssetsView, meta: { navKey: 'admin-reference-assets' } },
          { path: 'tasks', name: 'admin-tasks', component: AdminTasksView, meta: { navKey: 'admin-tasks' } },
          { path: 'audits', name: 'admin-audits', component: AdminAuditsView, meta: { navKey: 'admin-audits' } },
          { path: 'recharge', name: 'admin-recharge', component: AdminRechargeView, meta: { navKey: 'admin-recharge' } },
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
    if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') return { name: 'workspaces' }
    if (to.meta.guestOnly && authStore.user) return { name: 'workspaces' }
  })
  return router
}
