<script setup>
import { useI18n } from 'vue-i18n'
import { localizeAccountText } from '../../utils/accountLocalization'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import { getCreditLedger } from '../../api/account'
import AppButton from '../ui/AppButton.vue'
import AppDataTable from '../ui/AppDataTable.vue'
import AppDateTime from '../ui/AppDateTime.vue'
import AppSelect from '../ui/AppSelect.vue'
import EmptyState from '../ui/EmptyState.vue'
import { getApiErrorMessage } from '../../utils/apiError'

const { t, locale } = useI18n()
const typeOptions = computed(() => ([
  { value: 'all', label: t('records.allTypes') },
  { value: 'recharge', label: t('records.recharge') },
  { value: 'consume', label: t('records.consume') },
  { value: 'refund', label: t('records.refund') },
  { value: 'system', label: t('records.system') },
]))
const mediaOptions = computed(() => ([
  { value: 'all', label: t('records.allMedia') },
  { value: 'text', label: t('records.text') },
  { value: 'image', label: t('records.image') },
  { value: 'video', label: t('records.video') },
  { value: 'audio', label: t('records.audio') },
]))
const timeOptions = computed(() => ([
  { value: 'today', label: t('records.today') },
  { value: '7days', label: t('records.sevenDays') },
  { value: '30days', label: t('records.thirtyDays') },
  { value: 'custom', label: t('records.custom') },
]))
const typeLabels = computed(() => ({ recharge: t('records.recharge'), consume: t('records.consume'), refund: t('records.refund'), system: t('records.system') }))
const mediaLabels = computed(() => ({ text: t('records.text'), image: t('records.image'), video: t('records.video'), audio: t('records.audio') }))
const columns = computed(() => ([
  { key: 'created_at', label: t('records.time'), width: '158px' },
  { key: 'type', label: t('records.type'), width: '78px' },
  { key: 'media_type', label: t('records.mediaType'), width: '92px' },
  { key: 'model', label: t('records.model'), width: '220px', class: 'credit-model-cell' },
  { key: 'note', label: t('records.note') },
  { key: 'delta', label: t('records.delta'), width: '92px', align: 'right' },
  { key: 'balance_after', label: t('records.balance'), width: '92px', align: 'right' },
]))
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
    error.value = requestError
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  return new Date(value).toLocaleString(locale.value, {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

watch(() => [filters.type, filters.media_type, filters.time], ([, , time], previous) => {
  if (time !== 'custom' || previous?.[2] === 'custom') load()
})
onMounted(load)
</script>

<template>
  <header class="account-section-heading"><h1>{{ t('records.ledger') }}</h1><p>{{ t('records.ledgerSubtitle') }}</p></header>

  <div class="credit-filters">
    <AppSelect v-model="filters.type" :options="typeOptions" :aria-label="t('records.creditType')" />
    <AppSelect v-model="filters.media_type" :options="mediaOptions" :aria-label="t('records.mediaType')" />
    <AppSelect v-model="filters.time" :options="timeOptions" :aria-label="t('records.timeRange')" />
    <template v-if="filters.time === 'custom'">
      <AppDateTime v-model="filters.start" :aria-label="t('records.startTime')" :placeholder="t('records.startTime')" />
      <span class="credit-filters__separator">{{ t('records.to') }}</span>
      <AppDateTime v-model="filters.end" :aria-label="t('records.endTime')" :placeholder="t('records.endTime')" />
      <AppButton type="button" variant="primary" :disabled="!filters.start && !filters.end" @click="load()">
        <Search :size="15" />{{ t('records.search') }}
      </AppButton>
    </template>
  </div>

  <EmptyState v-if="error" compact tone="error" :title="t('records.ledgerError')" :description="getApiErrorMessage(error, t('records.ledgerError'))">
    <AppButton variant="primary" @click="load(result.page)">{{ t('records.reload') }}</AppButton>
  </EmptyState>
  <AppDataTable
    v-else
    :columns="columns"
    :items="result.items"
    :loading="loading"
    :loading-title="t('records.ledgerLoading')"
    :empty-title="t('records.ledgerEmpty')"
    :empty-description="t('records.ledgerFilterEmpty')"
    min-width="960px"
    :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }"
    @page-change="load"
  >
    <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
    <template #cell-type="{ item }"><span class="credit-type" :class="`credit-type--${item.type}`">{{ typeLabels[item.type] }}</span></template>
    <template #cell-media_type="{ value }">{{ mediaLabels[value] || '—' }}</template>
    <template #cell-model="{ value }">{{ value || '—' }}</template>
    <template #cell-note="{ value }">{{ localizeAccountText(value) || '—' }}</template>
    <template #cell-delta="{ value }"><span class="credit-delta" :class="value >= 0 ? 'positive' : 'negative'">{{ value > 0 ? '+' : '' }}{{ value }}</span></template>
    <template #cell-balance_after="{ value }"><span class="credit-balance">{{ value }}</span></template>
  </AppDataTable>
</template>
