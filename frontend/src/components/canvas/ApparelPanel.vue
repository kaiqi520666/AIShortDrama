<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Image, LoaderCircle, Plus, Shirt, Trash2 } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { createEmptyApparelItem, parseApparelProfile } from '../../config/canvas/apparel'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppInput from '../ui/AppInput.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const reference = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'image'))
const items = computed(() => props.data.items || [])
const selectedModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.model) || capabilityStore.defaultTextModel)
const modelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const compositionOptions = computed(() => ([{ value: 'single', label: t('canvas.singleApparel') }, { value: 'set', label: t('canvas.outfitSet') }]))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => failure.value || props.data.generationError || (!reference.value?.data.asset
  ? t('canvas.uploadApparelFirst')
  : insufficientCredits.value ? t('canvas.insufficientCredits', { p0: estimatedCredits.value }) : ''))
const canSubmit = computed(() => !running.value && reference.value?.data.asset && !insufficientCredits.value)

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, status: 'ready', generationError: '' })
}

function updateItem(id, value) {
  updateData({ items: items.value.map((item) => item.id === id ? { ...item, ...value } : item) })
}

function addItem() {
  updateData({ items: [...items.value, createEmptyApparelItem()], compositionType: items.value.length ? 'set' : props.data.compositionType })
}

function removeItem(id) {
  const nextItems = items.value.filter((item) => item.id !== id)
  updateData({ items: nextItems, compositionType: nextItems.length > 1 ? 'set' : 'single' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (items.value.length && !await confirm({
    title: t('canvas.recognizeApparelAgain'),
    message: t('canvas.replaceApparelItems'),
    confirmText: t('canvas.recognizeAgain'),
  })) return

  await runTextTask(streamReversePrompt, {
    workspace_id: store.workspaceId,
    node_id: props.nodeId,
    model: selectedModel.value.id,
    media_type: 'image',
    media_url: reference.value.data.asset,
    prompt: props.data.prompt || '',
    response_mode: 'apparel_profile',
  }, {
    failureMessage: t('canvas.apparelRecognitionFailed'),
    onSuccess: parseApparelProfile,
  })
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel apparel-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Shirt :size="16" />{{ t('canvas.apparelRecognition') }}</span>
      <small>{{ items.length ? t('canvas.itemCount', { p0: items.length }) : t('canvas.waitingRecognition') }}</small>
    </header>

    <div class="apparel-profile-head">
      <div class="apparel-reference" :class="{ empty: !reference?.data.asset }">
        <AppImageHoverPreview v-if="reference?.data.asset" :src="reference.data.asset" :preview-src="buildOssImageUrl(reference.data.asset, { width: 1200, quality: 90 })" :alt="t('canvas.apparelReference')">
          <img :src="buildOssImageUrl(reference.data.asset, { width: 220, quality: 82 })" :alt="t('canvas.apparelReference')" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <Image v-else :size="22" />
      </div>
      <label><span>{{ t('canvas.profileType') }}</span><AppSelect :model-value="data.compositionType" :options="compositionOptions" :aria-label="t('canvas.apparelProfileType')" @update:model-value="updateData({ compositionType: $event })" /></label>
      <label><span>{{ t('canvas.outfitSummary') }}</span><AppInput :model-value="data.summary" maxlength="240" :placeholder="t('canvas.outfitSummaryPlaceholder')" @input="updateData({ summary: $event.target.value })" /></label>
    </div>

    <section class="apparel-items-section">
      <div class="apparel-section-title"><span>{{ t('canvas.itemList') }}</span><AppButton variant="soft" @click="addItem"><Plus :size="14" />{{ t('canvas.addItem') }}</AppButton></div>
      <div class="apparel-items">
        <article v-for="(item, index) in items" :key="item.id" class="apparel-item">
          <div class="apparel-item-head">
            <input type="checkbox" :checked="item.enabled" :aria-label="t('canvas.enableItem', { p0: index + 1 })" @change="updateItem(item.id, { enabled: $event.target.checked })" />
            <span>{{ t('canvas.itemNumber', { p0: index + 1 }) }}</span>
            <AppInput :model-value="item.name" :aria-label="t('canvas.itemName')" :placeholder="t('canvas.itemName')" @input="updateItem(item.id, { name: $event.target.value })" />
            <AppInput :model-value="item.category" :aria-label="t('canvas.itemCategory')" :placeholder="t('canvas.category')" @input="updateItem(item.id, { category: $event.target.value })" />
            <AppButton icon-only variant="ghost" :aria-label="t('canvas.deleteItem', { p0: index + 1 })" @click="removeItem(item.id)"><Trash2 :size="14" /></AppButton>
          </div>
          <div class="apparel-item-fields">
            <label><span>{{ t('canvas.color') }}</span><AppInput :model-value="item.color" :placeholder="t('canvas.colorPlaceholder')" @input="updateItem(item.id, { color: $event.target.value })" /></label>
            <label><span>{{ t('canvas.fabric') }}</span><AppInput :model-value="item.material" :placeholder="t('canvas.fabricPlaceholder')" @input="updateItem(item.id, { material: $event.target.value })" /></label>
            <label><span>{{ t('canvas.silhouette') }}</span><AppInput :model-value="item.silhouette" :placeholder="t('canvas.silhouettePlaceholder')" @input="updateItem(item.id, { silhouette: $event.target.value })" /></label>
            <label><span>{{ t('canvas.designDetails') }}</span><AppInput :model-value="item.details" :placeholder="t('canvas.designDetailsPlaceholder')" @input="updateItem(item.id, { details: $event.target.value })" /></label>
          </div>
        </article>
        <p v-if="!items.length" class="apparel-empty">{{ t('canvas.apparelEmpty') }}</p>
      </div>
    </section>

    <AppTextarea class="apparel-extra" :model-value="data.prompt" rows="2" maxlength="600" :placeholder="t('canvas.apparelPromptPlaceholder')" @input="updateData({ prompt: $event.target.value })" />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedModel.id" :options="modelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateData({ model: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.recognizing') : t('canvas.recognizeApparel')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
