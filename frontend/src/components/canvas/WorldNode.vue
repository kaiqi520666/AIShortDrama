<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { Globe2, ScrollText } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { worldOptions, worldReady } from '../../config/canvas/drama'
import { canvasLabel } from '../../i18n/canvas'
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

const { updateNodeData } = useVueFlow()
const step = computed(() => props.data.workflowStep || 'setting')
const setting = computed(() => props.data.setting || {})
const world = computed(() => props.data.world || {})
const completed = computed(() => worldReady(world.value))
const optionMap = computed(() => Object.fromEntries(Object.entries(worldOptions).map(([key, values]) => [key, values.map((value) => ({ value, label: canvasLabel(value) }))])))
const resultFields = computed(() => [
  ['overview', t('canvas.worldOverview')],
  ['timeSpace', t('canvas.worldTimeSpace')],
  ['society', t('canvas.worldSociety')],
  ['rules', t('canvas.worldRules')],
  ['conflict', t('canvas.worldConflict')],
  ['visualGuide', t('canvas.worldVisualGuide')],
])

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
        :first-label="t('canvas.settingInput')"
        :second-label="t('canvas.worldResult')"
        :aria-label="t('canvas.worldSteps')"
        @update:step="updateNodeData(id, { workflowStep: $event })"
      />

      <template v-if="step === 'setting'">
        <div class="structured-node-summary product-step-summary">
          <span><Globe2 :size="15" />{{ t('canvas.creationConditions') }}</span>
          <small>{{ t('canvas.sharedDramaSetting') }}</small>
        </div>
        <div class="product-fields two-columns">
          <label><span>{{ t('canvas.genre') }}</span><AppSelect :model-value="setting.genre" :options="optionMap.genre" :aria-label="t('canvas.genre')" @update:model-value="updateSetting('genre', $event)" /></label>
          <label><span>{{ t('canvas.era') }}</span><AppSelect :model-value="setting.era" :options="optionMap.era" :aria-label="t('canvas.era')" @update:model-value="updateSetting('era', $event)" /></label>
          <label><span>{{ t('canvas.location') }}</span><AppInput class="nodrag nopan" :model-value="setting.location" :placeholder="t('canvas.locationPlaceholder')" @input="updateSetting('location', $event.target.value)" /></label>
          <label><span>{{ t('canvas.civilization') }}</span><AppSelect :model-value="setting.civilization" :options="optionMap.civilization" :aria-label="t('canvas.civilizationLabel')" @update:model-value="updateSetting('civilization', $event)" /></label>
          <label><span>{{ t('canvas.visualStyle') }}</span><AppSelect :model-value="setting.visualStyle" :options="optionMap.visualStyle" :aria-label="t('canvas.visualStyle')" @update:model-value="updateSetting('visualStyle', $event)" /></label>
          <label><span>{{ t('canvas.tone') }}</span><AppSelect :model-value="setting.tone" :options="optionMap.tone" :aria-label="t('canvas.tone')" @update:model-value="updateSetting('tone', $event)" /></label>
        </div>
        <label class="product-field-wide"><span>{{ t('canvas.socialRules') }}</span><AppInput class="nodrag nopan" :model-value="setting.ruleSeed" :placeholder="t('canvas.socialRulesPlaceholder')" @input="updateSetting('ruleSeed', $event.target.value)" /></label>
      </template>

      <template v-else>
        <div class="structured-node-summary product-step-summary">
          <span><ScrollText :size="15" />{{ t('canvas.worldSetting') }}</span>
          <small>{{ completed ? t('canvas.generated') : t('canvas.pendingGeneration') }}</small>
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
