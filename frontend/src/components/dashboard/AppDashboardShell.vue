<script setup>
import { ClipboardList, History, LayoutDashboard, PanelsTopLeft, ReceiptText, Tags, UsersRound } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

defineProps({
  activeItem: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
  isAdmin: Boolean,
})
const emit = defineEmits(['logout'])

const accountItems = [
  { id: 'overview', label: '账户概览', icon: LayoutDashboard, to: { name: 'account' } },
  { id: 'credits', label: '积分明细', icon: ReceiptText, to: { name: 'credits' } },
  { id: 'pricing', label: '计费标准', icon: Tags, to: { name: 'pricing' } },
]
const adminItems = [
  { id: 'admin-users', label: '用户管理', icon: UsersRound, to: { name: 'admin-users' } },
  { id: 'admin-pricing', label: '模型计费', icon: Tags, to: { name: 'admin-pricing' } },
  { id: 'admin-tasks', label: '生成任务', icon: ClipboardList, to: { name: 'admin-tasks' } },
  { id: 'admin-audits', label: '操作审计', icon: History, to: { name: 'admin-audits' } },
]
</script>

<template>
  <main class="dashboard-shell">
    <header class="dashboard-header">
      <AppBrand to="/dashboard/workspaces" />
      <AppHeaderAccountControls
        :username="username"
        :credit-balance="creditBalance"
        :credit-frozen="creditFrozen"
        @logout="emit('logout')"
      />
    </header>

    <div class="dashboard-body">
      <aside class="dashboard-sidebar">
        <nav class="dashboard-nav" aria-label="用户中心">
          <RouterLink class="dashboard-nav__item" :class="{ active: activeItem === 'workspaces' }" :to="{ name: 'workspaces' }">
            <PanelsTopLeft :size="16" /><span>工作台</span>
          </RouterLink>
          <div class="dashboard-nav__group">
            <RouterLink
              v-for="item in accountItems"
              :key="item.id"
              class="dashboard-nav__item"
              :class="{ active: activeItem === item.id }"
              :to="item.to"
            >
              <component :is="item.icon" :size="16" /><span>{{ item.label }}</span>
            </RouterLink>
          </div>
          <div v-if="isAdmin" class="dashboard-nav__group dashboard-nav__group--admin">
            <small>后台管理</small>
            <RouterLink v-for="item in adminItems" :key="item.id" class="dashboard-nav__item" :class="{ active: activeItem === item.id }" :to="item.to">
              <component :is="item.icon" :size="16" /><span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </nav>
      </aside>
      <section class="dashboard-content"><slot /></section>
    </div>
  </main>
</template>
