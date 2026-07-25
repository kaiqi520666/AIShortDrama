<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import { getCreditLedger } from '../../api/account'
import AppButton from '../ui/AppButton.vue'
import AppDataTable from '../ui/AppDataTable.vue'
import AppDateTime from '../ui/AppDateTime.vue'
import AppSelect from '../ui/AppSelect.vue'
import EmptyState from '../ui/EmptyState.vue'

const typeOptions = [
  { value: 'all', label: '全部类型' },
  { value: 'recharge', label: '充值' },
  { value: 'consume', label: '消费' },
  { value: 'refund', label: '退回' },
  { value: 'system', label: '系统' },
]
const mediaOptions = [
  { value: 'all', label: '全部模型类型' },
  { value: 'text', label: '文本' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
]
const timeOptions = [
  { value: 'today', label: '今日' },
  { value: '7days', label: '近 7 天' },
  { value: '30days', label: '近 30 天' },
  { value: 'custom', label: '自定义' },
]
const typeLabels = { recharge: '充值', consume: '消费', refund: '退回', system: '系统' }
const mediaLabels = { text: '文本', image: '图片', video: '视频', audio: '音频' }
const columns = [
  { key: 'created_at', label: '时间', width: '158px' },
  { key: 'type', label: '类型', width: '78px' },
  { key: 'media_type', label: '模型类型', width: '92px' },
  { key: 'model', label: '模型', width: '220px', class: 'credit-model-cell' },
  { key: 'note', label: '说明' },
  { key: 'delta', label: '积分变化', width: '92px', align: 'right' },
  { key: 'balance_after', label: '余额', width: '92px', align: 'right' },
]
const filters = reactive({ type: 'all', media_type: 'all', time: '30days', start: '', end: '' })
const result = ref({ items: [], page: 1, page_size: 20, total: 0 })
const loading = ref(true)
const error = ref('')

function beijingDate() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date())
}

function shiftDate(value, days) {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function dateParams() {
  const today = beijingDate()
  if (filters.time === 'custom') {
    return {
      start_at: filters.start ? `${filters.start}:00+08:00` : undefined,
      end_at: filters.end ? `${filters.end}:00+08:00` : undefined,
    }
  }
  const days = filters.time === 'today' ? 1 : filters.time === '7days' ? 7 : 30
  return {
    start_at: `${shiftDate(today, 1 - days)}T00:00:00+08:00`,
    end_at: `${shiftDate(today, 1)}T00:00:00+08:00`,
  }
}

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const response = await getCreditLedger({
      type: filters.type,
      media_type: filters.media_type,
      ...dateParams(),
      page,
      page_size: 20,
    })
    if (response.code !== 0) throw new Error(response.message)
    result.value = response.data
  } catch (requestError) {
    error.value = requestError.response?.data?.message || requestError.message || '积分明细加载失败'
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  return new Date(value).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

watch(() => [filters.type, filters.media_type, filters.time], ([, , time], previous) => {
  if (time !== 'custom' || previous?.[2] === 'custom') load()
})
onMounted(load)
</script>

<template>
  <header class="account-section-heading"><h1>积分明细</h1><p>查看充值、消费、退回与系统调整记录</p></header>

  <div class="credit-filters">
    <AppSelect v-model="filters.type" :options="typeOptions" aria-label="积分类型" />
    <AppSelect v-model="filters.media_type" :options="mediaOptions" aria-label="模型类型" />
    <AppSelect v-model="filters.time" :options="timeOptions" aria-label="时间范围" />
    <template v-if="filters.time === 'custom'">
      <AppDateTime v-model="filters.start" aria-label="开始时间" placeholder="开始时间" />
      <span class="credit-filters__separator">至</span>
      <AppDateTime v-model="filters.end" aria-label="结束时间" placeholder="结束时间" />
      <AppButton type="button" variant="primary" :disabled="!filters.start && !filters.end" @click="load()">
        <Search :size="15" />查询
      </AppButton>
    </template>
  </div>

  <EmptyState v-if="error" compact tone="error" title="积分明细加载失败" :description="error">
    <AppButton variant="primary" @click="load(result.page)">重新加载</AppButton>
  </EmptyState>
  <AppDataTable
    v-else
    :columns="columns"
    :items="result.items"
    :loading="loading"
    loading-title="正在加载积分明细"
    empty-title="暂无积分记录"
    empty-description="当前筛选条件下没有相关明细"
    min-width="960px"
    :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }"
    @page-change="load"
  >
    <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
    <template #cell-type="{ item }"><span class="credit-type" :class="`credit-type--${item.type}`">{{ typeLabels[item.type] }}</span></template>
    <template #cell-media_type="{ value }">{{ mediaLabels[value] || '—' }}</template>
    <template #cell-model="{ value }">{{ value || '—' }}</template>
    <template #cell-note="{ value }">{{ value || '—' }}</template>
    <template #cell-delta="{ value }"><span class="credit-delta" :class="value >= 0 ? 'positive' : 'negative'">{{ value > 0 ? '+' : '' }}{{ value }}</span></template>
    <template #cell-balance_after="{ value }"><span class="credit-balance">{{ value }}</span></template>
  </AppDataTable>
</template>
