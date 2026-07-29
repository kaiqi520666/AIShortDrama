<script setup>
import { computed } from 'vue'
import { Globe2, ScrollText } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { worldOptions, worldReady } from '../../config/canvas/drama'
import AppInput from '../ui/AppInput.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const { updateNodeData } = useVueFlow()
const step = computed(() => props.data.workflowStep || 'setting')
const setting = computed(() => props.data.setting || {})
const world = computed(() => props.data.world || {})
const completed = computed(() => worldReady(world.value))
const optionMap = Object.fromEntries(Object.entries(worldOptions).map(([key, values]) => [key, values.map((value) => ({ value, label: value }))]))
const resultFields = [
  ['overview', '世界概述'],
  ['timeSpace', '时空环境'],
  ['society', '社会结构与阵营'],
  ['rules', '运行规则与边界'],
  ['conflict', '核心矛盾'],
  ['visualGuide', '视觉基准'],
]

function updateSetting(key, value) {
  updateNodeData(props.id, { setting: { ...setting.value, [key]: value } })
}

function updateWorld(key, value) {
  updateNodeData(props.id, { world: { ...world.value, [key]: value }, status: 'ready' })
}
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Globe2" :selected="selected">
    <div class="product-node-content world-node-content nowheel" @keydown.stop>
      <ProductWorkflowSteps
        :step="step"
        :recognized="completed"
        first-step="setting"
        second-step="result"
        first-label="设定输入"
        second-label="世界观结果"
        aria-label="世界观创作步骤"
        @update:step="updateNodeData(id, { workflowStep: $event })"
      />

      <template v-if="step === 'setting'">
        <div class="structured-node-summary product-step-summary">
          <span><Globe2 :size="15" />创作条件</span>
          <small>短剧统一设定</small>
        </div>
        <div class="product-fields two-columns">
          <label><span>题材</span><AppSelect :model-value="setting.genre" :options="optionMap.genre" aria-label="题材" @update:model-value="updateSetting('genre', $event)" /></label>
          <label><span>时代</span><AppSelect :model-value="setting.era" :options="optionMap.era" aria-label="时代" @update:model-value="updateSetting('era', $event)" /></label>
          <label><span>地域</span><AppInput class="nodrag nopan" :model-value="setting.location" placeholder="例如：沿海小城" @input="updateSetting('location', $event.target.value)" /></label>
          <label><span>文明 / 科技</span><AppSelect :model-value="setting.civilization" :options="optionMap.civilization" aria-label="文明或科技" @update:model-value="updateSetting('civilization', $event)" /></label>
          <label><span>视觉风格</span><AppSelect :model-value="setting.visualStyle" :options="optionMap.visualStyle" aria-label="视觉风格" @update:model-value="updateSetting('visualStyle', $event)" /></label>
          <label><span>故事基调</span><AppSelect :model-value="setting.tone" :options="optionMap.tone" aria-label="故事基调" @update:model-value="updateSetting('tone', $event)" /></label>
        </div>
        <label class="product-field-wide"><span>社会规则</span><AppInput class="nodrag nopan" :model-value="setting.ruleSeed" placeholder="例如：记忆可以交易，但不能复制" @input="updateSetting('ruleSeed', $event.target.value)" /></label>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><ScrollText :size="15" />世界观设定</span>
          <small>{{ completed ? '已生成' : '待生成' }}</small>
        </div>
        <div class="world-result-fields">
          <label v-for="([key, label]) in resultFields" :key="key">
            <span>{{ label }}</span>
            <AppTextarea class="nodrag nopan" :model-value="world[key]" maxlength="600" @input="updateWorld(key, $event.target.value)" />
          </label>
        </div>
      </template>
    </div>
  </StructuredNodeShell>
</template>
