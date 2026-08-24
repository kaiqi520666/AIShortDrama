<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Search } from 'lucide-vue-next'
import { getAdminRechargeOrders } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const loading = ref(false)
const result = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', status: 'all', start_at: '', end_at: '' })
const statusOptions = [{ value: 'all', label: '全部状态' }, { value: 'pending', label: '待支付' }, { value: 'paid', label: '已支付' }, { value: 'failed', label: '失败' }]
const columns = [
  { key: 'user', label: '用户' },
  { key: 'out_trade_no', label: '订单号' },
  { key: 'amount_cents', label: '金额' },
  { key: 'credits', label: '基础 / 赠送 / 到账' },
  { key: 'status', label: '状态' },
  { key: 'created_at', label: '创建时间' },
  { key: 'paid_at', label: '支付时间' },
]

async function load(page = 1) {
  loading.value = true
  try {
    const params = { ...filters, page, page_size: result.page_size }
    if (!params.start_at) delete params.start_at
    if (!params.end_at) delete params.end_at
    const response = await getAdminRechargeOrders(params)
    if (response.code !== 0) throw new Error(response.message)
    Object.assign(result, response.data)
  } catch (error) { toast.error(getApiErrorMessage(error, '充值订单加载失败')) }
  finally { loading.value = false }
}

function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>RECHARGE ORDERS</span><h1>充值订单</h1><p>查询用户充值与支付到账记录</p></div><b>{{ result.total }} 个订单</b></header>
    <form class="admin-filters admin-filters--orders" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="用户、邮箱或订单号" /></label><AppSelect v-model="filters.status" :options="statusOptions" aria-label="支付状态" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form>
    <AppDataTable :columns="columns" :items="result.items" :loading="loading" loading-title="正在加载充值订单" empty-title="没有符合条件的充值订单" min-width="980px" :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }" @page-change="load">
      <template #cell-user="{ item }"><strong>{{ item.user.username }}</strong><small>{{ item.user.email }}</small></template>
      <template #cell-out_trade_no="{ item }"><strong>{{ item.out_trade_no }}</strong><small>{{ item.provider_trade_no || '—' }}</small></template>
      <template #cell-amount_cents="{ value }">¥{{ value / 100 }}</template>
      <template #cell-credits="{ item }">{{ item.base_credits }} / +{{ item.bonus_credits }} / {{ item.total_credits }}</template>
      <template #cell-status="{ item }"><span class="admin-status" :class="`is-${item.status}`">{{ ({ pending: '待支付', paid: '已支付', failed: '失败' })[item.status] }}</span></template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-paid_at="{ value }">{{ formatDate(value) }}</template>
    </AppDataTable>
  </section>
</template>
