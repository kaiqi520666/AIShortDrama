<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { CheckCircle2, Globe2, Image, Images, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { characterOptions, characterReady, characterVisualTypes } from '../../config/canvas/character'
import { canvasLabel } from '../../i18n/canvas'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppInput from '../ui/AppInput.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import ProductWorkflowSteps from './ProductWorkflowSteps.vue'
import StructuredNodeShell from './StructuredNodeShell.vue'

const { t } = useI18n()

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
const optionMap = computed(() => Object.fromEntries(Object.entries(characterOptions).map(([key, values]) => [key, values.map((value) => ({ value, label: canvasLabel(value) }))])))
const profileFields = computed(() => ([
  ['background', t('canvas.characterBackground')], ['appearance', t('canvas.characterAppearance')], ['personality', t('canvas.characterPersonality')],
  ['costume', t('canvas.characterCostume')], ['signature', t('canvas.characterSignature')], ['constraints', t('canvas.characterConstraints')],
]))

const worldNode = computed(() => store.incomingNodeByHandle(props.id, 'world'))
const referenceImage = computed(() => store.incomingNodeByHandle(props.id, 'reference'))
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
        :first-label="t('canvas.characterSetting')"
        :second-label="t('canvas.characterSheet')"
        :aria-label="t('canvas.characterSteps')"
        @update:step="updateNodeData(id, { workflowStep: $event })"
      />

      <div class="character-inputs">
        <div class="outfit-source" :class="{ empty: !worldNode }">
          <span class="outfit-source-preview"><Globe2 :size="18" /></span>
          <span><strong>{{ t('canvas.world') }}</strong><small>{{ worldNode?.data.title || t('canvas.waitingConnection') }}</small></span>
          <CheckCircle2 v-if="worldNode" :size="16" />
        </div>
        <div class="outfit-source" :class="{ empty: !referenceImage?.data.asset }">
          <span class="outfit-source-preview">
            <img v-if="referenceImage?.data.asset" :src="buildOssImageUrl(referenceImage.data.asset, { width: 160, quality: 80 })" :alt="t('canvas.characterReference')" referrerpolicy="no-referrer" />
            <Image v-else :size="18" />
          </span>
          <span><strong>{{ t('canvas.characterReference') }}</strong><small>{{ referenceImage?.data.asset ? referenceImage.data.title : t('canvas.optional') }}</small></span>
          <CheckCircle2 v-if="referenceImage?.data.asset" :size="16" />
        </div>
      </div>

      <template v-if="step === 'profile'">
        <div class="product-fields two-columns character-setting-fields">
          <label><span>{{ t('canvas.roleType') }}</span><AppSelect :model-value="setting.roleType" :options="optionMap.roleType" :aria-label="t('canvas.roleType')" @update:model-value="updateSetting('roleType', $event)" /></label>
          <label><span>{{ t('canvas.gender') }}</span><AppSelect :model-value="setting.gender" :options="optionMap.gender" :aria-label="t('canvas.gender')" @update:model-value="updateSetting('gender', $event)" /></label>
          <label><span>{{ t('canvas.ageStage') }}</span><AppSelect :model-value="setting.ageStage" :options="optionMap.ageStage" :aria-label="t('canvas.ageStage')" @update:model-value="updateSetting('ageStage', $event)" /></label>
          <label><span>{{ t('canvas.visualStyle') }}</span><AppSelect :model-value="setting.visualStyle" :options="optionMap.visualStyle" :aria-label="t('canvas.characterVisualStyle')" @update:model-value="updateSetting('visualStyle', $event)" /></label>
          <label><span>{{ t('canvas.characterName') }}</span><AppInput class="nodrag nopan" :model-value="profile.name" :placeholder="t('canvas.aiPlaceholder')" @input="updateProfile('name', $event.target.value)" /></label>
          <label><span>{{ t('canvas.identity') }}</span><AppInput class="nodrag nopan" :model-value="profile.identity" :placeholder="t('canvas.aiPlaceholder')" @input="updateProfile('identity', $event.target.value)" /></label>
        </div>
        <div class="character-profile-fields">
          <label v-for="([key, label]) in profileFields" :key="key">
            <span>{{ label }}</span>
            <AppTextarea class="nodrag nopan" :model-value="profile[key]" maxlength="600" :placeholder="t('canvas.aiPlaceholder')" @input="updateProfile(key, $event.target.value)" />
          </label>
        </div>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><Images :size="15" />{{ t('canvas.characterSheets') }}</span>
          <small>{{ t('canvas.createdSheets', { p0: generatedNodes.length }) }}</small>
        </div>
        <div class="product-visual-tags character-visual-tags">
          <span v-for="item in characterVisualTypes" :key="item.id">{{ canvasLabel(item.label) }}</span>
        </div>
        <div class="product-creation-settings-summary">
          <span>{{ data.imageModel }}</span><span>{{ data.aspectRatio }}</span><span>{{ data.resolution }}</span>
        </div>
        <label v-if="mainReferenceOptions.length" class="character-main-reference">
          <span>{{ t('canvas.mainReference') }}</span>
          <AppSelect :model-value="data.mainReferenceNodeId" :options="mainReferenceOptions" :aria-label="t('canvas.characterMainReference')" @update:model-value="updateNodeData(id, { mainReferenceNodeId: $event })" />
        </label>
      </template>
    </div>
  </StructuredNodeShell>
</template>
