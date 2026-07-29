<script setup>
import { computed } from 'vue'
import { CheckCircle2, Globe2, Image, Images, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { characterOptions, characterReady, characterVisualTypes } from '../../config/canvas/character'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
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

const store = useCanvasStore()
const { updateNodeData } = useVueFlow()
const targetHandles = [{ id: 'world', top: '90px' }, { id: 'reference', top: '146px' }]
const step = computed(() => props.data.workflowStep || 'profile')
const setting = computed(() => props.data.setting || {})
const profile = computed(() => props.data.profile || {})
const completed = computed(() => characterReady(profile.value))
const optionMap = Object.fromEntries(Object.entries(characterOptions).map(([key, values]) => [key, values.map((value) => ({ value, label: value }))]))
const profileFields = [
  ['background', '人物背景'], ['appearance', '外貌特征'], ['personality', '性格与动机'],
  ['costume', '服装造型'], ['signature', '标志性特征'], ['constraints', '一致性约束'],
]

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.id && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const worldNode = computed(() => inputNode('world'))
const referenceImage = computed(() => inputNode('reference'))
const generatedNodes = computed(() => (props.data.generatedNodeIds || []).map((id) => store.nodes.find((node) => node.id === id)).filter(Boolean))
const mainReferenceOptions = computed(() => generatedNodes.value.filter((node) => node.data.asset).map((node) => ({ value: node.id, label: node.data.title })))

function updateSetting(key, value) {
  updateNodeData(props.id, { setting: { ...setting.value, [key]: value } })
}

function updateProfile(key, value) {
  updateNodeData(props.id, { profile: { ...profile.value, [key]: value }, status: 'ready' })
}
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="UserRound" :selected="selected" :target-handles="targetHandles">
    <div class="product-node-content character-node-content nowheel" @keydown.stop>
      <ProductWorkflowSteps
        :step="step"
        :recognized="completed"
        first-step="profile"
        second-step="visual"
        first-label="角色设定"
        second-label="设定图"
        aria-label="角色创作步骤"
        @update:step="updateNodeData(id, { workflowStep: $event })"
      />

      <div class="character-inputs">
        <div class="outfit-source" :class="{ empty: !worldNode }">
          <span class="outfit-source-preview"><Globe2 :size="18" /></span>
          <span><strong>世界观</strong><small>{{ worldNode?.data.title || '等待连接' }}</small></span>
          <CheckCircle2 v-if="worldNode" :size="16" />
        </div>
        <div class="outfit-source" :class="{ empty: !referenceImage?.data.asset }">
          <span class="outfit-source-preview">
            <img v-if="referenceImage?.data.asset" :src="buildOssImageUrl(referenceImage.data.asset, { width: 160, quality: 80 })" alt="角色参考图" referrerpolicy="no-referrer" />
            <Image v-else :size="18" />
          </span>
          <span><strong>角色参考图</strong><small>{{ referenceImage?.data.asset ? referenceImage.data.title : '可选' }}</small></span>
          <CheckCircle2 v-if="referenceImage?.data.asset" :size="16" />
        </div>
      </div>

      <template v-if="step === 'profile'">
        <div class="product-fields two-columns character-setting-fields">
          <label><span>角色定位</span><AppSelect :model-value="setting.roleType" :options="optionMap.roleType" aria-label="角色定位" @update:model-value="updateSetting('roleType', $event)" /></label>
          <label><span>性别</span><AppSelect :model-value="setting.gender" :options="optionMap.gender" aria-label="性别" @update:model-value="updateSetting('gender', $event)" /></label>
          <label><span>年龄阶段</span><AppSelect :model-value="setting.ageStage" :options="optionMap.ageStage" aria-label="年龄阶段" @update:model-value="updateSetting('ageStage', $event)" /></label>
          <label><span>视觉风格</span><AppSelect :model-value="setting.visualStyle" :options="optionMap.visualStyle" aria-label="角色视觉风格" @update:model-value="updateSetting('visualStyle', $event)" /></label>
          <label><span>角色姓名</span><AppInput class="nodrag nopan" :model-value="profile.name" placeholder="可留空由 AI 生成" @input="updateProfile('name', $event.target.value)" /></label>
          <label><span>身份职业</span><AppInput class="nodrag nopan" :model-value="profile.identity" placeholder="可留空由 AI 生成" @input="updateProfile('identity', $event.target.value)" /></label>
        </div>
        <div class="character-profile-fields">
          <label v-for="([key, label]) in profileFields" :key="key">
            <span>{{ label }}</span>
            <AppTextarea class="nodrag nopan" :model-value="profile[key]" maxlength="600" placeholder="可留空由 AI 生成" @input="updateProfile(key, $event.target.value)" />
          </label>
        </div>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><Images :size="15" />角色设定图</span>
          <small>{{ generatedNodes.length }}/3 已创建</small>
        </div>
        <div class="product-visual-tags character-visual-tags">
          <span v-for="item in characterVisualTypes" :key="item.id">{{ item.label }}</span>
        </div>
        <div class="product-creation-settings-summary">
          <span>{{ data.imageModel }}</span><span>{{ data.aspectRatio }}</span><span>{{ data.resolution }}</span>
        </div>
        <label v-if="mainReferenceOptions.length" class="character-main-reference">
          <span>主参考图</span>
          <AppSelect :model-value="data.mainReferenceNodeId" :options="mainReferenceOptions" aria-label="角色主参考图" @update:model-value="updateNodeData(id, { mainReferenceNodeId: $event })" />
        </label>
      </template>
    </div>
  </StructuredNodeShell>
</template>
