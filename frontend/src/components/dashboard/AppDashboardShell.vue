<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown, ClipboardList, CreditCard, FileText, Gift, History, Image, Images, LayoutDashboard, ListOrdered, PanelsTopLeft, ReceiptText, Settings2, Shirt, Tags, UsersRound } from 'lucide-vue-next'
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
const { t } = useI18n()

const accountItems = [
  { id: 'overview', key: 'overview', icon: LayoutDashboard, to: { name: 'account' } },
  { id: 'recharge', key: 'recharge', icon: CreditCard, to: { name: 'recharge' } },
  { id: 'generations', key: 'generations', icon: ClipboardList, to: { name: 'generations' } },
  { id: 'credits', key: 'credits', icon: ReceiptText, to: { name: 'credits' } },
  { id: 'pricing', key: 'pricing', icon: Tags, to: { name: 'pricing' } },
]
const adminGroups = [
  {
    id: 'operations',
    key: 'operations',
    items: [
      { id: 'admin-overview', key: 'adminOverview', icon: LayoutDashboard, to: { name: 'admin-overview' } },
      { id: 'admin-tasks', key: 'tasks', icon: ClipboardList, to: { name: 'admin-tasks' } },
      { id: 'admin-audits', key: 'audits', icon: History, to: { name: 'admin-audits' } },
    ],
  },
  {
    id: 'content',
    key: 'content',
    items: [
      { id: 'admin-models', key: 'models', icon: PanelsTopLeft, to: { name: 'admin-models' } },
      { id: 'admin-image-settings', key: 'imageSettings', icon: Image, to: { name: 'admin-image-product' } },
      { id: 'admin-commerce-templates', key: 'commerceTemplates', icon: FileText, to: { name: 'admin-commerce-ugc' } },
      { id: 'admin-apparel-templates', key: 'apparelTemplates', icon: Shirt, to: { name: 'admin-apparel-showcase' } },
    ],
  },
  {
    id: 'resources',
    key: 'resources',
    items: [
      { id: 'admin-users', key: 'users', icon: UsersRound, to: { name: 'admin-users' } },
      { id: 'admin-reference-assets', key: 'referenceAssets', icon: Images, to: { name: 'admin-reference-assets' } },
    ],
  },
  {
    id: 'finance',
    key: 'finance',
    items: [
      { id: 'admin-credit-policy', key: 'creditPolicy', icon: Gift, to: { name: 'admin-credit-policy' } },
      { id: 'admin-recharge-policy', key: 'rechargePolicy', icon: Settings2, to: { name: 'admin-recharge-policy' } },
      { id: 'admin-recharge-tiers', key: 'rechargeTiers', icon: ListOrdered, to: { name: 'admin-recharge-tiers' } },
      { id: 'admin-recharge-orders', key: 'rechargeOrders', icon: CreditCard, to: { name: 'admin-recharge-orders' } },
      { id: 'admin-model-pricing', key: 'modelPricing', icon: Tags, to: { name: 'admin-model-pricing' } },
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
        <nav class="dashboard-nav" :aria-label="t('navigation.userCenter')">
          <RouterLink class="dashboard-nav__item" :class="{ active: activeItem === 'workspaces' }" :to="{ name: 'workspaces' }">
            <PanelsTopLeft :size="16" /><span>{{ t('common.workspaces') }}</span>
          </RouterLink>
          <div class="dashboard-nav__group">
            <small>{{ t('navigation.userCenter') }}</small>
            <RouterLink
              v-for="item in accountItems"
              :key="item.id"
              class="dashboard-nav__item"
              :class="{ active: activeItem === item.id }"
              :to="item.to"
            >
              <component :is="item.icon" :size="16" /><span>{{ t(`navigation.${item.key}`) }}</span>
            </RouterLink>
          </div>
          <div v-if="isAdmin" class="dashboard-nav__group dashboard-nav__group--admin">
            <small>{{ t('navigation.admin') }}</small>
            <div v-for="group in adminGroups" :key="group.id" class="dashboard-nav__section">
              <button
                type="button"
                class="dashboard-nav__section-toggle"
                :aria-expanded="openAdminGroup === group.id"
                :aria-controls="`admin-group-${group.id}`"
                @click="toggleAdminGroup(group.id)"
              >
                <span>{{ t(`navigation.${group.key}`) }}</span><ChevronDown :size="15" :class="{ 'is-expanded': openAdminGroup === group.id }" />
              </button>
              <div v-show="openAdminGroup === group.id" :id="`admin-group-${group.id}`" class="dashboard-nav__section-items">
                <RouterLink v-for="item in group.items" :key="item.id" class="dashboard-nav__item" :class="{ active: activeItem === item.id }" :to="item.to">
                  <component :is="item.icon" :size="16" /><span>{{ t(`navigation.${item.key}`) }}</span>
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
