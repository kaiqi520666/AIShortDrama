<script setup>
import { LayoutDashboard, PanelsTopLeft, ReceiptText, ShieldCheck, Tags, UserPlus, UserRound } from 'lucide-vue-next'
import AppAccountMenu from '../account/AppAccountMenu.vue'
import AppBrand from '../ui/AppBrand.vue'
import AppThemeSwitch from '../ui/AppThemeSwitch.vue'

defineProps({
  activeItem: { type: String, required: true },
  username: { type: String, required: true },
})
const emit = defineEmits(['logout'])

const accountItems = [
  { id: 'overview', label: '账户概览', icon: LayoutDashboard },
  { id: 'credits', label: '积分明细', icon: ReceiptText },
  { id: 'pricing', label: '计费标准', icon: Tags },
  { id: 'profile', label: '个人信息', icon: UserRound },
  { id: 'security', label: '安全设置', icon: ShieldCheck },
  { id: 'invite', label: '邀请', icon: UserPlus },
]
</script>

<template>
  <main class="dashboard-shell">
    <header class="dashboard-header">
      <AppBrand to="/workspaces" />
      <div class="dashboard-header__actions">
        <AppThemeSwitch />
        <AppAccountMenu :username="username" @logout="emit('logout')" />
      </div>
    </header>

    <div class="dashboard-body">
      <aside class="dashboard-sidebar">
        <nav class="dashboard-nav" aria-label="用户中心">
          <RouterLink class="dashboard-nav__item" :class="{ active: activeItem === 'workspaces' }" to="/workspaces">
            <PanelsTopLeft :size="16" /><span>工作台</span>
          </RouterLink>
          <div class="dashboard-nav__group">
            <span class="dashboard-nav__label">账户</span>
            <RouterLink
              v-for="item in accountItems"
              :key="item.id"
              class="dashboard-nav__item"
              :class="{ active: activeItem === item.id }"
              :to="{ name: 'account', query: { section: item.id } }"
            >
              <component :is="item.icon" :size="16" /><span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </nav>
      </aside>
      <section class="dashboard-content"><slot /></section>
    </div>
  </main>
</template>
