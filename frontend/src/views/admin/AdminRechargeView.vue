<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Pencil, Plus, Search } from 'lucide-vue-next'
import { createAdminRechargeTier, getAdminRechargeOrders, getAdminRechargeTiers, updateAdminRechargeTier } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const view = ref('tiers')
const loading = ref(false)
const tiers = ref([])
const orders = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', status: 'all', start_at: '', end_at: '' })
const dialog = reactive({ tier: null, open: false, reason: '', amount: '', bonus: '', enabled: 'true', submitting: false })
const statusOptions = [{ value: 'all', label: '全部状态' }, { value: 'pending', label: '待支付' }, { value: 'paid', label: '已支付' }, { value: 'failed', label: '失败' }]
const enabledOptions = [{ value: 'true', label: '启用' }, { value: 'false', label: '停用' }]

async function loadTiers() {
  loading.value = true
  try {
    const result = await getAdminRechargeTiers()
    if (result.code !== 0) throw new Error(result.message)
    tiers.value = result.data
  } catch (error) { toast.error(error.response?.data?.message || error.message || '充值阶梯加载失败') }
  finally { loading.value = false }
}

async function loadOrders(page = 1) {
  loading.value = true
  try {
    const params = { ...filters, page, page_size: orders.page_size }
    if (!params.start_at) delete params.start_at
    if (!params.end_at) delete params.end_at
    const result = await getAdminRechargeOrders(params)
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(orders, result.data)
  } catch (error) { toast.error(error.response?.data?.message || error.message || '充值订单加载失败') }
  finally { loading.value = false }
}

function switchView(next) {
  view.value = next
  next === 'tiers' ? loadTiers() : loadOrders(1)
}

function openTier(tier = null) {
  Object.assign(dialog, {
    tier, open: true, reason: '',
    amount: tier ? String(tier.min_amount_cents / 100) : '',
    bonus: tier ? String(tier.bonus_rate_bps / 100) : '',
    enabled: String(tier?.enabled ?? true),
  })
}

async function saveTier() {
  dialog.submitting = true
  try {
    const payload = {
      reason: dialog.reason,
      min_amount_cents: Number(dialog.amount) * 100,
      bonus_rate_bps: Math.round(Number(dialog.bonus) * 100),
      enabled: dialog.enabled === 'true',
    }
    const result = dialog.tier
      ? await updateAdminRechargeTier(dialog.tier.id, payload)
      : await createAdminRechargeTier(payload)
    if (result.code !== 0) throw new Error(result.message)
    dialog.open = false
    toast.success('充值阶梯已保存')
    await loadTiers()
  } catch (error) { toast.error(error.response?.data?.message || error.message || '保存失败') }
  finally { dialog.submitting = false }
}

function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
onMounted(loadTiers)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>RECHARGE CONTROL</span><h1>充值管理</h1><p>管理赠送阶梯并查询微信支付订单</p></div><b>{{ view === 'tiers' ? `${tiers.length} 个阶梯` : `${orders.total} 个订单` }}</b></header>
    <div class="admin-segments"><AppButton :variant="view === 'tiers' ? 'primary' : 'soft'" @click="switchView('tiers')">充值阶梯</AppButton><AppButton :variant="view === 'orders' ? 'primary' : 'soft'" @click="switchView('orders')">充值订单</AppButton></div>

    <template v-if="view === 'tiers'">
      <div class="admin-toolbar"><p>金额越高，赠送比例不得降低，最高可设置 30%</p><AppButton variant="primary" @click="openTier()"><Plus :size="15" />新增阶梯</AppButton></div>
      <EmptyState v-if="loading" loading title="正在加载充值阶梯" />
      <div v-else class="admin-table-wrap"><table class="admin-table"><thead><tr><th>起充金额</th><th>赠送比例</th><th>示例到账积分</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead><tbody><tr v-for="tier in tiers" :key="tier.id"><td><strong>¥{{ tier.min_amount_cents / 100 }}</strong></td><td>{{ tier.bonus_rate_bps / 100 }}%</td><td>{{ Math.floor(tier.min_amount_cents * 1000 / 3500) + Math.floor(Math.floor(tier.min_amount_cents * 1000 / 3500) * tier.bonus_rate_bps / 10000) }}</td><td><span class="admin-status" :class="tier.enabled ? 'is-active' : 'is-disabled'">{{ tier.enabled ? '启用' : '停用' }}</span></td><td>{{ formatDate(tier.updated_at) }}</td><td><AppButton size="sm" variant="soft" @click="openTier(tier)"><Pencil :size="14" />编辑</AppButton></td></tr></tbody></table></div>
    </template>

    <template v-else>
      <form class="admin-filters" @submit.prevent="loadOrders(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="用户、邮箱或订单号" /></label><AppSelect v-model="filters.status" :options="statusOptions" aria-label="支付状态" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form>
      <EmptyState v-if="loading" loading title="正在加载充值订单" />
      <div v-else class="admin-table-wrap"><table class="admin-table"><thead><tr><th>用户</th><th>订单号</th><th>金额</th><th>基础 / 赠送 / 到账</th><th>状态</th><th>创建时间</th><th>支付时间</th></tr></thead><tbody><tr v-for="item in orders.items" :key="item.id"><td><strong>{{ item.user.username }}</strong><small>{{ item.user.email }}</small></td><td><strong>{{ item.out_trade_no }}</strong><small>{{ item.provider_trade_no || '—' }}</small></td><td>¥{{ item.amount_cents / 100 }}</td><td>{{ item.base_credits }} / +{{ item.bonus_credits }} / {{ item.total_credits }}</td><td><span class="admin-status" :class="`is-${item.status}`">{{ ({ pending: '待支付', paid: '已支付', failed: '失败' })[item.status] }}</span></td><td>{{ formatDate(item.created_at) }}</td><td>{{ formatDate(item.paid_at) }}</td></tr></tbody></table><EmptyState v-if="!orders.items.length" title="没有符合条件的充值订单" /></div>
      <AdminPagination :page="orders.page" :page-size="orders.page_size" :total="orders.total" @change="loadOrders" />
    </template>

    <AdminDialog v-if="dialog.open" v-model:reason="dialog.reason" :title="dialog.tier ? '编辑充值阶梯' : '新增充值阶梯'" description="修改只影响后续创建的订单" :submitting="dialog.submitting" @close="dialog.open = false" @submit="saveTier"><div class="admin-form-grid"><label class="admin-field"><span>起充金额（元）</span><AppInput v-model="dialog.amount" type="number" min="35" max="3500" step="1" required /></label><label class="admin-field"><span>赠送比例（%）</span><AppInput v-model="dialog.bonus" type="number" min="0" max="30" step="0.01" required /></label><label class="admin-field"><span>状态</span><AppSelect v-model="dialog.enabled" :options="enabledOptions" aria-label="启用状态" /></label></div></AdminDialog>
  </section>
</template>
