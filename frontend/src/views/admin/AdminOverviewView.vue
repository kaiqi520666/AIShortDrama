<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Activity, CircleDollarSign, Clock3, Layers3, RefreshCw, WalletCards } from 'lucide-vue-next'
import { getAdminDashboard } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppTabs from '../../components/ui/AppTabs.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const days = ref(7)
const dashboard = ref(null)
const loading = ref(false)
const error = ref('')
const periods = computed(() => [1, 7, 30].map((value) => ({ value, label: t('admin.overview.lastDays', { days: n(value) }) })))
const modelColumns = computed(() => [
  { key: 'model', label: t('admin.model') },
  { key: 'count', label: t('admin.overview.calls'), align: 'right' },
])
const metrics = computed(() => {
  const value = dashboard.value
  if (!value) return []
  return [
    { label: t('admin.overview.paidRecharge'), value: formatMoney(value.recharge_amount_cents), detail: t('admin.overview.orders', { count: n(value.recharge_order_count) }), icon: CircleDollarSign },
    { label: t('admin.overview.consumed'), value: n(value.consumed_credits), detail: t('admin.overview.settled'), icon: WalletCards },
    { label: t('navigation.tasks'), value: n(value.task_count), detail: t('admin.overview.rateValue', { rate: formatRate(value.success_rate) }), icon: Activity },
    { label: t('admin.overview.queue'), value: n(value.queued_task_count), detail: value.queue_depth == null ? t('admin.overview.redisUnavailable') : t('admin.overview.queueDepth', { count: n(value.queue_depth) }), icon: Clock3 },
  ]
})

function formatMoney(cents) {
  return n(Number(cents || 0) / 100, { style: 'currency', currency: 'CNY' })
}

function formatRate(rate) {
  return rate == null ? '—' : n(Number(rate), { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getAdminDashboard(days.value)
    if (result.code !== 0) throw new Error(result.message)
    dashboard.value = result.data
  } catch (requestError) {
    error.value = getApiErrorMessage(requestError, t('admin.overview.loadFailed'))
    toast.error(error.value)
  } finally {
    loading.value = false
  }
}

function changePeriod(value) {
  days.value = Number(value)
  load()
}

onMounted(load)
</script>

<template>
  <section class="admin-page admin-overview">
    <header class="admin-page__header">
      <div><span>{{ t('navigation.operations') }}</span><h1>{{ t('navigation.adminOverview') }}</h1><p>{{ t('admin.overview.description') }}</p></div>
      <AppButton variant="soft" :disabled="loading" :title="t('admin.overview.refreshAria')" @click="load"><RefreshCw :size="15" :class="{ 'is-spinning': loading }" />{{ t('admin.overview.refresh') }}</AppButton>
    </header>

    <div class="admin-overview__controls">
      <AppTabs :model-value="days" :options="periods" :aria-label="t('admin.overview.period')" @update:model-value="changePeriod" />
      <small>{{ t('admin.overview.periodDescription', { days: n(days) }) }}</small>
    </div>

    <EmptyState v-if="error" tone="error" compact :title="t('admin.overview.loadFailed')" :description="error">
      <AppButton variant="primary" @click="load">{{ t('common.reload') }}</AppButton>
    </EmptyState>
    <template v-else>
      <div class="admin-metrics" :aria-busy="loading">
        <article v-for="metric in metrics" :key="metric.label" class="admin-metric">
          <component :is="metric.icon" :size="18" />
          <span>{{ metric.label }}</span><strong>{{ metric.value }}</strong><small>{{ metric.detail }}</small>
        </article>
      </div>

      <div class="admin-overview__grid">
        <section class="admin-summary-block">
          <header><div><Layers3 :size="16" /><h2>{{ t('admin.overview.taskStatus') }}</h2></div><small>{{ t('admin.overview.tasks', { count: n(dashboard?.task_count || 0) }) }}</small></header>
          <dl class="admin-summary-list">
            <div><dt>{{ t('admin.overview.succeeded') }}</dt><dd>{{ n(dashboard?.succeeded_count || 0) }}</dd></div>
            <div><dt>{{ t('admin.overview.failed') }}</dt><dd>{{ n(dashboard?.failed_count || 0) }}</dd></div>
            <div><dt>{{ t('admin.overview.timeout') }}</dt><dd>{{ n(dashboard?.timeout_count || 0) }}</dd></div>
            <div><dt>{{ t('admin.overview.rate') }}</dt><dd>{{ formatRate(dashboard?.success_rate) }}</dd></div>
          </dl>
        </section>
        <section class="admin-summary-block">
          <header><div><Activity :size="16" /><h2>{{ t('admin.overview.modelCalls') }}</h2></div><small>{{ t('admin.overview.byCreation') }}</small></header>
          <AppDataTable :columns="modelColumns" :items="dashboard?.model_calls || []" :loading="loading" :loading-title="t('admin.overview.loadingCalls')" :empty-title="t('admin.overview.emptyCalls')" min-width="360px">
            <template #cell-count="{ value }">{{ n(value) }}</template>
          </AppDataTable>
        </section>
      </div>
    </template>
  </section>
</template>
