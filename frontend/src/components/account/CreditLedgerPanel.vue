<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Search } from 'lucide-vue-next'
import { getCreditLedger } from '../../api/account'
import AppButton from '../ui/AppButton.vue'
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
const filters = reactive({ type: 'all', media_type: 'all', time: '30days', start: '', end: '' })
const result = ref({ items: [], page: 1, page_size: 20, total: 0 })
const loading = ref(true)
const error = ref('')
const totalPages = computed(() => Math.max(1, Math.ceil(result.value.total / result.value.page_size)))

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

  <EmptyState v-if="loading" compact loading title="正在加载积分明细" />
  <EmptyState v-else-if="error" compact tone="error" title="积分明细加载失败" :description="error">
    <AppButton variant="primary" @click="load(result.page)">重新加载</AppButton>
  </EmptyState>
  <EmptyState v-else-if="!result.items.length" compact title="暂无积分记录" description="当前筛选条件下没有相关明细" />

  <template v-else>
    <div class="credit-table-wrap">
      <table class="credit-table">
        <thead><tr><th>时间</th><th>类型</th><th>模型类型</th><th>模型</th><th>说明</th><th>积分变化</th><th>余额</th></tr></thead>
        <tbody>
          <tr v-for="item in result.items" :key="item.id">
            <td data-label="时间">{{ formatDate(item.created_at) }}</td>
            <td data-label="类型"><span class="credit-type" :class="`credit-type--${item.type}`">{{ typeLabels[item.type] }}</span></td>
            <td data-label="模型类型">{{ mediaLabels[item.media_type] || '—' }}</td>
            <td data-label="模型">{{ item.model || '—' }}</td>
            <td data-label="说明">{{ item.note || '—' }}</td>
            <td data-label="积分变化" class="credit-delta" :class="item.delta >= 0 ? 'positive' : 'negative'">{{ item.delta > 0 ? '+' : '' }}{{ item.delta }}</td>
            <td data-label="余额" class="credit-balance">{{ item.balance_after }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="credit-pagination">
      <span>共 {{ result.total }} 条</span>
      <div>
        <AppButton icon-only aria-label="上一页" :disabled="result.page <= 1" @click="load(result.page - 1)"><ChevronLeft :size="16" /></AppButton>
        <span>{{ result.page }} / {{ totalPages }}</span>
        <AppButton icon-only aria-label="下一页" :disabled="result.page >= totalPages" @click="load(result.page + 1)"><ChevronRight :size="16" /></AppButton>
      </div>
    </footer>
  </template>
</template>
