<script setup>
import { LayoutDashboard, PanelsTopLeft, ReceiptText, Tags } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

defineProps({
  activeItem: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
})
const emit = defineEmits(['logout'])

const accountItems = [
  { id: 'overview', label: '账户概览', icon: LayoutDashboard, to: { name: 'account' } },
  { id: 'credits', label: '积分明细', icon: ReceiptText, to: { name: 'credits' } },
  { id: 'pricing', label: '计费标准', icon: Tags, to: { name: 'pricing' } },
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
        </nav>
      </aside>
      <section class="dashboard-content"><slot /></section>
    </div>
  </main>
</template>
