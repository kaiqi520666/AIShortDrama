<script setup>
import { useI18n } from 'vue-i18n'
import { computed, onMounted, ref } from 'vue'
import { getCredits } from '../../api/credits'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import AppButton from '../ui/AppButton.vue'
import AppDataTable from '../ui/AppDataTable.vue'
import EmptyState from '../ui/EmptyState.vue'
import { getApiErrorMessage } from '../../utils/apiError'

const { t } = useI18n()
const mediaLabels = computed(() => ({ text: t('records.text'), image: t('records.image'), video: t('records.video'), audio: t('records.audio') }))
const mediaOrder = { text: 0, image: 1, video: 2, audio: 3 }
const unitLabels = computed(() => ({ request: t('records.requestUnit'), image: t('records.imageUnit'), second: t('records.second'), minute: t('records.minute') }))
const capabilityStore = useModelCapabilitiesStore()
const modelLabels = computed(() => Object.fromEntries([
  ...capabilityStore.textModels,
  ...capabilityStore.imageModels,
  ...capabilityStore.videoModels,
  capabilityStore.audioCapability?.model,
].filter(Boolean).map(({ id, label }) => [id, label])))
const columns = computed(() => ([
  { key: 'media_type', label: t('records.mediaType'), width: '110px' },
  { key: 'model', label: t('records.model'), width: '34%' },
  { key: 'specification', label: t('records.specification'), width: '90px' },
  { key: 'billing_unit', label: t('records.billingUnit'), width: '110px' },
  { key: 'unit_credits', label: t('records.creditRate'), width: '190px' },
]))
const rules = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [response] = await Promise.all([getCredits(), capabilityStore.load()])
    if (response.code !== 0) throw new Error(response.message)
    rules.value = response.data.prices.toSorted((a, b) =>
      mediaOrder[a.media_type] - mediaOrder[b.media_type]
      || a.model.localeCompare(b.model)
      || a.specification.localeCompare(b.specification),
    )
  } catch (requestError) {
    error.value = requestError
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <header class="account-section-heading"><h1>{{ t('records.pricing') }}</h1><p>{{ t('records.pricingSubtitle') }}</p></header>

  <EmptyState v-if="error" compact tone="error" :title="t('records.pricingError')" :description="getApiErrorMessage(error, t('records.pricingError'))">
    <AppButton variant="primary" @click="load">{{ t('records.reload') }}</AppButton>
  </EmptyState>
  <AppDataTable
    v-else
    :columns="columns"
    :items="rules"
    :row-key="(rule) => `${rule.media_type}-${rule.model}-${rule.specification}`"
    :loading="loading"
    :loading-title="t('records.pricingLoading')"
    :empty-title="t('records.pricingEmpty')"
    min-width="760px"
  >
    <template #cell-media_type="{ value }"><span class="pricing-media-type">{{ mediaLabels[value] }}</span></template>
    <template #cell-model="{ value }"><strong>{{ modelLabels[value] || value }}</strong><small>{{ value }}</small></template>
    <template #cell-specification="{ value }">{{ value || '—' }}</template>
    <template #cell-billing_unit="{ value }">{{ t('records.perUnit', { unit: unitLabels[value] }) }}</template>
    <template #cell-unit_credits="{ item }">
      <span class="pricing-points"><strong>{{ t('records.credits', { count: $n(item.unit_credits) }) }}</strong><span>/ {{ unitLabels[item.billing_unit] }}</span><small v-if="item.media_type === 'audio'">{{ t('records.frozen', { count: $n(item.freeze_credits) }) }}</small></span>
    </template>
  </AppDataTable>
</template>
