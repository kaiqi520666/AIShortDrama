<script setup>
import { computed, watch } from 'vue'
import { LoaderCircle, Megaphone } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { copyOutputTypes } from '../../config/canvas/ecommerce'
import { startGenerationPolling } from '../../services/generationPolling'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const outputLabel = computed(() => copyOutputTypes.find((item) => item.value === props.data.outputType)?.label || '核心卖点')
const { updateNodeData } = useVueFlow()

watch(
  () => [props.data.generationTaskId, props.data.status],
  ([taskId, status]) => {
    if (taskId && status === 'generating') startGenerationPolling(taskId, props.id, updateNodeData)
  },
  { immediate: true },
)
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Megaphone" :selected="selected" has-target>
    <div class="selling-copy-node-content nodrag nopan nowheel">
      <div class="structured-node-summary">
        <span><Megaphone :size="15" />{{ outputLabel }}</span>
        <small v-if="data.status === 'generating'" class="copy-running"><LoaderCircle :size="12" />生成中</small>
        <small v-else>{{ data.content ? `${data.content.length} 字` : '等待生成' }}</small>
      </div>
      <div v-if="data.status === 'failed'" class="structured-node-error">{{ data.generationError || '文案生成失败' }}</div>
      <div v-else-if="data.content" class="selling-copy-result">{{ data.content }}</div>
      <div v-else class="selling-copy-empty">
        <Megaphone :size="34" stroke-width="1.35" />
        <span>选择节点后配置文案类型</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
