<script setup>
import { ref, watch } from 'vue'
import { ChevronDown, ClipboardList, CreditCard, FileText, History, Image, Images, LayoutDashboard, PanelsTopLeft, ReceiptText, Shirt, Tags, UsersRound } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

const props = defineProps({
  activeItem: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
  isAdmin: Boolean,
})
const emit = defineEmits(['logout'])

const accountItems = [
  { id: 'overview', label: '账户概览', icon: LayoutDashboard, to: { name: 'account' } },
  { id: 'recharge', label: '积分充值', icon: CreditCard, to: { name: 'recharge' } },
  { id: 'generations', label: '生成记录', icon: ClipboardList, to: { name: 'generations' } },
  { id: 'credits', label: '积分明细', icon: ReceiptText, to: { name: 'credits' } },
  { id: 'pricing', label: '计费标准', icon: Tags, to: { name: 'pricing' } },
]
const adminGroups = [
  {
    id: 'operations',
    label: '运营概览',
    items: [
      { id: 'admin-overview', label: '后台概览', icon: LayoutDashboard, to: { name: 'admin-overview' } },
      { id: 'admin-tasks', label: '生成任务', icon: ClipboardList, to: { name: 'admin-tasks' } },
      { id: 'admin-audits', label: '操作审计', icon: History, to: { name: 'admin-audits' } },
    ],
  },
  {
    id: 'content',
    label: '内容配置',
    items: [
      { id: 'admin-models', label: '模型管理', icon: PanelsTopLeft, to: { name: 'admin-models' } },
      { id: 'admin-pricing', label: '计费规则', icon: Tags, to: { name: 'admin-pricing' } },
      { id: 'admin-image-settings', label: '出图设置', icon: Image, to: { name: 'admin-image-product' } },
      { id: 'admin-commerce-templates', label: '电商模板', icon: FileText, to: { name: 'admin-commerce-ugc' } },
      { id: 'admin-apparel-templates', label: '服饰模板', icon: Shirt, to: { name: 'admin-apparel-showcase' } },
    ],
  },
  {
    id: 'resources',
    label: '用户资源',
    items: [
      { id: 'admin-users', label: '用户管理', icon: UsersRound, to: { name: 'admin-users' } },
      { id: 'admin-reference-assets', label: '系统素材库', icon: Images, to: { name: 'admin-reference-assets' } },
    ],
  },
  {
    id: 'finance',
    label: '财务管理',
    items: [
      { id: 'admin-recharge', label: '充值管理', icon: CreditCard, to: { name: 'admin-recharge' } },
    ],
  },
]
const openAdminGroup = ref('operations')

function toggleAdminGroup(groupId) {
  openAdminGroup.value = openAdminGroup.value === groupId ? '' : groupId
}

watch(() => props.activeItem, (activeItem) => {
  const group = adminGroups.find(({ items }) => items.some((item) => item.id === activeItem))
  if (group) openAdminGroup.value = group.id
}, { immediate: true })
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
            <small>个人中心</small>
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
            <div v-for="group in adminGroups" :key="group.label" class="dashboard-nav__section">
              <button
                type="button"
                class="dashboard-nav__section-toggle"
                :aria-expanded="openAdminGroup === group.id"
                :aria-controls="`admin-group-${group.id}`"
                @click="toggleAdminGroup(group.id)"
              >
                <span>{{ group.label }}</span><ChevronDown :size="15" :class="{ 'is-expanded': openAdminGroup === group.id }" />
              </button>
              <div v-show="openAdminGroup === group.id" :id="`admin-group-${group.id}`" class="dashboard-nav__section-items">
                <RouterLink v-for="item in group.items" :key="item.id" class="dashboard-nav__item" :class="{ active: activeItem === item.id }" :to="item.to">
                  <component :is="item.icon" :size="16" /><span>{{ item.label }}</span>
                </RouterLink>
              </div>
            </div>
          </div>
        </nav>
      </aside>
      <section class="dashboard-content"><slot /></section>
    </div>
  </main>
</template>
