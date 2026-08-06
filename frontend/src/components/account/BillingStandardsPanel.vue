<script setup>
import { computed, onMounted, ref } from 'vue'
import { getCredits } from '../../api/credits'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import AppButton from '../ui/AppButton.vue'
import AppDataTable from '../ui/AppDataTable.vue'
import EmptyState from '../ui/EmptyState.vue'

const mediaLabels = { text: '文本', image: '图片', video: '视频', audio: '音频' }
const mediaOrder = { text: 0, image: 1, video: 2, audio: 3 }
const unitLabels = { request: '次', image: '张', second: '秒', minute: '分钟' }
const capabilityStore = useModelCapabilitiesStore()
const modelLabels = computed(() => Object.fromEntries([
  ...capabilityStore.textModels,
  ...capabilityStore.imageModels,
  ...capabilityStore.videoModels,
  capabilityStore.audioCapability?.model,
].filter(Boolean).map(({ id, label }) => [id, label])))
const columns = [
  { key: 'media_type', label: '模型类型', width: '110px' },
  { key: 'model', label: '模型', width: '34%' },
  { key: 'specification', label: '规格', width: '90px' },
  { key: 'billing_unit', label: '计费方式', width: '110px' },
  { key: 'unit_credits', label: '积分标准', width: '190px' },
]
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
    error.value = requestError.response?.data?.message || requestError.message || '计费标准加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <header class="account-section-heading"><h1>计费标准</h1><p>生成任务按下列积分标准结算</p></header>

  <EmptyState v-if="error" compact tone="error" title="计费标准加载失败" :description="error">
    <AppButton variant="primary" @click="load">重新加载</AppButton>
  </EmptyState>
  <AppDataTable
    v-else
    :columns="columns"
    :items="rules"
    :row-key="(rule) => `${rule.media_type}-${rule.model}-${rule.specification}`"
    :loading="loading"
    loading-title="正在加载计费标准"
    empty-title="暂无计费标准"
    min-width="760px"
  >
    <template #cell-media_type="{ value }"><span class="pricing-media-type">{{ mediaLabels[value] }}</span></template>
    <template #cell-model="{ value }"><strong>{{ modelLabels[value] || value }}</strong><small>{{ value }}</small></template>
    <template #cell-specification="{ value }">{{ value || '—' }}</template>
    <template #cell-billing_unit="{ value }">按{{ unitLabels[value] }}</template>
    <template #cell-unit_credits="{ item }">
      <span class="pricing-points"><strong>{{ item.unit_credits }} 积分</strong><span>/ {{ unitLabels[item.billing_unit] }}</span><small v-if="item.media_type === 'audio'">提交时冻结 {{ item.freeze_credits }} 积分</small></span>
    </template>
  </AppDataTable>
</template>
