<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
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
const { t, n } = useI18n()
const loading = ref(false)
const result = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', status: 'all', start_at: '', end_at: '' })
const statusOptions = computed(() => [{ value: 'all', label: t('admin.allStatuses') }, ...['pending', 'paid', 'failed'].map((value) => ({ value, label: t(`admin.orders.${value}`) }))])
const columns = computed(() => [
  { key: 'user', label: t('common.user') },
  { key: 'out_trade_no', label: t('admin.orders.number') },
  { key: 'amount_cents', label: t('admin.orders.amount') },
  { key: 'credits', label: t('admin.orders.credits') },
  { key: 'status', label: t('admin.status') },
  { key: 'created_at', label: t('common.createdAt') },
  { key: 'paid_at', label: t('admin.orders.paidAt') },
])

async function load(page = 1) {
  loading.value = true
  try {
    const params = { ...filters, page, page_size: result.page_size }
    if (!params.start_at) delete params.start_at
    if (!params.end_at) delete params.end_at
    const response = await getAdminRechargeOrders(params)
    if (response.code !== 0) throw new Error(response.message)
    Object.assign(result, response.data)
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.orders.loadFailed'))) }
  finally { loading.value = false }
}

function formatDate(value) { return value ? formatDateTime(value, { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'medium' }) : '—' }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.finance') }}</span><h1>{{ t('navigation.rechargeOrders') }}</h1><p>{{ t('admin.orders.description') }}</p></div><b>{{ t('admin.orders.count', { count: n(result.total) }) }}</b></header>
    <form class="admin-filters admin-filters--orders" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" :placeholder="t('admin.orders.search')" /></label><AppSelect v-model="filters.status" :options="statusOptions" :aria-label="t('admin.orders.status')" /><AppDateTime v-model="filters.start_at" :aria-label="t('common.startTime')" :placeholder="t('common.startTime')" /><AppDateTime v-model="filters.end_at" :aria-label="t('common.endTime')" :placeholder="t('common.endTime')" /><AppButton type="submit" variant="primary">{{ t('admin.query') }}</AppButton></form>
    <AppDataTable :columns="columns" :items="result.items" :loading="loading" :loading-title="t('admin.orders.loading')" :empty-title="t('admin.orders.empty')" min-width="980px" :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }" @page-change="load">
      <template #cell-user="{ item }"><strong>{{ item.user.username }}</strong><small>{{ item.user.email }}</small></template>
      <template #cell-out_trade_no="{ item }"><strong>{{ item.out_trade_no }}</strong><small>{{ item.provider_trade_no || '—' }}</small></template>
      <template #cell-amount_cents="{ value }">{{ n(value / 100, { style: 'currency', currency: 'CNY' }) }}</template>
      <template #cell-credits="{ item }">{{ n(item.base_credits) }} / +{{ n(item.bonus_credits) }} / {{ n(item.total_credits) }}</template>
      <template #cell-status="{ item }"><span class="admin-status" :class="`is-${item.status}`">{{ t(`admin.orders.${item.status}`) }}</span></template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-paid_at="{ value }">{{ formatDate(value) }}</template>
    </AppDataTable>
  </section>
</template>
