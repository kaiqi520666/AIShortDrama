<script setup>
import { onMounted, ref } from 'vue'
import { getCredits } from '../../api/credits'
import { audioModel } from '../../config/audioModels'
import { imageModels } from '../../config/imageModels'
import { reverseModels } from '../../config/reverseModels'
import { videoModels } from '../../config/videoModels'
import AppButton from '../ui/AppButton.vue'
import EmptyState from '../ui/EmptyState.vue'

const mediaLabels = { text: '文本', image: '图片', video: '视频', audio: '音频' }
const mediaOrder = { text: 0, image: 1, video: 2, audio: 3 }
const unitLabels = { request: '次', image: '张', second: '秒', minute: '分钟' }
const modelLabels = Object.fromEntries([
  ...reverseModels,
  ...imageModels,
  ...videoModels,
  audioModel,
].map(({ id, label }) => [id, label]))
const rules = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await getCredits()
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

  <EmptyState v-if="loading" compact loading title="正在加载计费标准" />
  <EmptyState v-else-if="error" compact tone="error" title="计费标准加载失败" :description="error">
    <AppButton variant="primary" @click="load">重新加载</AppButton>
  </EmptyState>
  <EmptyState v-else-if="!rules.length" compact title="暂无计费标准" />

  <div v-else class="pricing-table-wrap">
    <table class="pricing-table">
      <thead><tr><th>模型类型</th><th>模型</th><th>规格</th><th>计费方式</th><th>积分标准</th></tr></thead>
      <tbody>
        <tr v-for="rule in rules" :key="`${rule.media_type}-${rule.model}-${rule.specification}`">
          <td data-label="模型类型"><span class="pricing-media-type">{{ mediaLabels[rule.media_type] }}</span></td>
          <td data-label="模型"><strong>{{ modelLabels[rule.model] || rule.model }}</strong><small>{{ rule.model }}</small></td>
          <td data-label="规格">{{ rule.specification || '—' }}</td>
          <td data-label="计费方式">按{{ unitLabels[rule.billing_unit] }}</td>
          <td data-label="积分标准" class="pricing-points">
            <strong>{{ rule.unit_credits }} 积分</strong><span>/ {{ unitLabels[rule.billing_unit] }}</span>
            <small v-if="rule.media_type === 'audio'">提交时冻结 {{ rule.freeze_credits }} 积分</small>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
