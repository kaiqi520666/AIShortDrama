<script setup>
import { computed, onMounted, ref } from 'vue'
import { Activity, CircleDollarSign, Clock3, Layers3, RefreshCw, WalletCards } from 'lucide-vue-next'
import { getAdminDashboard } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppTabs from '../../components/ui/AppTabs.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const days = ref(7)
const dashboard = ref(null)
const loading = ref(false)
const error = ref('')
const periods = [
  { value: 1, label: '近 1 天' },
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
]
const modelColumns = [
  { key: 'model', label: '模型' },
  { key: 'count', label: '调用次数', align: 'right' },
]
const metrics = computed(() => {
  const value = dashboard.value
  if (!value) return []
  return [
    { label: '已支付充值', value: formatMoney(value.recharge_amount_cents), detail: `${value.recharge_order_count} 笔订单`, icon: CircleDollarSign },
    { label: '已消耗积分', value: value.consumed_credits.toLocaleString('zh-CN'), detail: '已完成任务结算', icon: WalletCards },
    { label: '生成任务', value: value.task_count.toLocaleString('zh-CN'), detail: `成功率 ${formatRate(value.success_rate)}`, icon: Activity },
    { label: '队列积压', value: value.queued_task_count.toLocaleString('zh-CN'), detail: value.queue_depth == null ? 'Redis 队列不可用' : `Redis 深度 ${value.queue_depth}`, icon: Clock3 },
  ]
})

function formatMoney(cents) {
  return `¥${(Number(cents || 0) / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
}

function formatRate(rate) {
  return rate == null ? '—' : `${(Number(rate) * 100).toFixed(1)}%`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getAdminDashboard(days.value)
    if (result.code !== 0) throw new Error(result.message)
    dashboard.value = result.data
  } catch (requestError) {
    error.value = getApiErrorMessage(requestError, '后台概览加载失败')
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
      <div><span>OPERATIONS OVERVIEW</span><h1>后台概览</h1><p>汇总充值、积分、生成任务与队列运行状态</p></div>
      <AppButton variant="soft" :disabled="loading" title="刷新概览" @click="load"><RefreshCw :size="15" :class="{ 'is-spinning': loading }" />刷新</AppButton>
    </header>

    <div class="admin-overview__controls">
      <AppTabs :model-value="days" :options="periods" aria-label="统计周期" @update:model-value="changePeriod" />
      <small>统计周期：最近 {{ days }} 天</small>
    </div>

    <EmptyState v-if="error" tone="error" compact title="后台概览加载失败" :description="error">
      <AppButton variant="primary" @click="load">重新加载</AppButton>
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
          <header><div><Layers3 :size="16" /><h2>任务状态</h2></div><small>{{ dashboard?.task_count || 0 }} 个任务</small></header>
          <dl class="admin-summary-list">
            <div><dt>成功</dt><dd>{{ dashboard?.succeeded_count || 0 }}</dd></div>
            <div><dt>失败</dt><dd>{{ dashboard?.failed_count || 0 }}</dd></div>
            <div><dt>超时</dt><dd>{{ dashboard?.timeout_count || 0 }}</dd></div>
            <div><dt>成功率</dt><dd>{{ formatRate(dashboard?.success_rate) }}</dd></div>
          </dl>
        </section>
        <section class="admin-summary-block">
          <header><div><Activity :size="16" /><h2>模型调用</h2></div><small>按任务创建时间统计</small></header>
          <AppDataTable :columns="modelColumns" :items="dashboard?.model_calls || []" :loading="loading" loading-title="正在加载模型调用" empty-title="当前周期暂无模型调用" min-width="360px" />
        </section>
      </div>
    </template>
  </section>
</template>
