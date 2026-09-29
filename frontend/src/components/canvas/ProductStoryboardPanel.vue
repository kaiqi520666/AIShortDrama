<script setup>
import { useI18n } from 'vue-i18n'
import { canvasTemplateText } from '../../i18n/canvas'
import { computed, ref } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, ImagePlus, Images, LoaderCircle, Package, UserRound, X } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { productPromptContext } from '../../config/canvas/ecommerce'
import {
  buildStoryboardReferenceManifest,
  buildProductStoryboardRequest,
  getStoryboardProductLimit,
  getStoryboardTemplateOption,
  MAX_STORYBOARD_CHARACTERS,
  MAX_STORYBOARD_REFERENCES,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
  storyboardSegmentCount,
  storyboardShotCount,
} from '../../config/canvas/productStoryboard'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppAssetPickerModal from '../assets/AppAssetPickerModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const { t } = useI18n()

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const capabilityStore = useModelCapabilitiesStore()
const contentTemplateStore = useContentTemplatesStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const characterPickerOpen = ref(false)
const characterAssetPickerOpen = ref(false)
const pendingCharacterAsset = ref(null)
const editingCharacterReferenceId = ref('')
const productPickerOpen = ref(false)
const editingProductReferenceId = ref('')
const productNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const referenceManifest = computed(() => buildStoryboardReferenceManifest(props.data.characterReferences, props.data.productReferences))
const productReferences = computed(() => referenceManifest.value.products)
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const storyboardTemplates = computed(() => ['product_storyboard', 'commerce_drama']
  .map((key) => getStoryboardTemplateOption(contentTemplateStore.templates?.[key]))
  .filter((item) => item?.enabled))
const selectedTemplateOption = computed(() => storyboardTemplates.value.find((item) => item.key === props.data.templateKey) || storyboardTemplates.value[0])
const template = computed(() => contentTemplateStore.templates?.[selectedTemplateOption.value?.key])
const templateEnabled = computed(() => Boolean(selectedTemplateOption.value && template.value))
const storyboardDurations = computed(() => selectedTemplateOption.value?.durations || [])
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const segmentCount = computed(() => storyboardSegmentCount(props.data.duration, storyboardDurations.value))
const shots = computed(() => storyboardShotCount(15))
const recommended = computed(() => recommendStoryboardSettings(15, props.data.videoAspectRatio, capabilityStore.defaultImageModel))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const videoAspectRatios = computed(() => capabilityStore.defaultVideoModel.aspectRatios)
const ratioOptions = computed(() => videoAspectRatios.value.map((value) => ({ value, label: value })))
const characterReferences = computed(() => referenceManifest.value.characters)
const totalReferenceCount = computed(() => characterReferences.value.length + productReferences.value.length)
const productLimit = computed(() => getStoryboardProductLimit(characterReferences.value.length))
const message = computed(() => failure.value || props.data.generationError || (!templateEnabled.value
  ? t('canvas.storyboardTemplateDisabled')
  : !productNode.value
  ? t('canvas.connectProductCreationFirst')
  : !productReferences.value.length
    ? t('canvas.selectProductReferenceFirst')
    : !productContext.value
      ? t('canvas.completeProductRecognitionFirst')
      : insufficientCredits.value ? t('canvas.insufficientCredits', { p0: estimatedCredits.value }) : ''))
const canSubmit = computed(() => templateEnabled.value && !running.value && productNode.value && productReferences.value.length && productContext.value && !insufficientCredits.value)

function selectTemplate(option) {
  if (!option || option.key === selectedTemplateOption.value?.key) return
  updateData({
    templateKey: option.key,
    templateId: option.id,
    templateVersion: contentTemplateStore.templates[option.key].version,
    duration: option.durations.includes(Number(props.data.duration)) ? Number(props.data.duration) : option.durations[0],
  })
}

function updateData(value) {
  failure.value = ''
  const hasProducts = Object.prototype.hasOwnProperty.call(value, 'productReferences')
  const hasCharacters = Object.prototype.hasOwnProperty.call(value, 'characterReferences')
  const manifest = hasProducts || hasCharacters
    ? buildStoryboardReferenceManifest(
      hasCharacters ? value.characterReferences : characterReferences.value,
      hasProducts ? value.productReferences : productReferences.value,
    )
    : null
  const normalizedValue = manifest
    ? { ...value, productReferences: manifest.products, characterReferences: manifest.characters }
    : value
  updateNodeData(props.nodeId, { ...normalizedValue, generationError: '' })
  if (manifest) {
    store.syncProductStoryboardReferences(
      props.nodeId,
      manifest.products,
      manifest.characters,
    )
  }
}

function selectCharacter(item) {
  if (!editingCharacterReferenceId.value && totalReferenceCount.value >= MAX_STORYBOARD_REFERENCES) return closeCharacterPicker()
  if (characterReferences.value.some((reference) => reference.id === item.id && reference.id !== editingCharacterReferenceId.value)) return closeCharacterPicker()
  const selected = {
    id: item.id,
    name: item.name,
    url: item.url,
    mediaType: item.mediaType || 'image',
    assetUrl: item.seedanceAssetUrl,
    groupId: item.seedanceGroupId,
    assetId: item.assetId || null,
    pickerKind: item.pickerKind || 'character',
    seedanceStatus: item.seedanceStatus || 'unregistered',
  }
  updateData({
    characterReferences: editingCharacterReferenceId.value
      ? characterReferences.value.map((reference) => reference.id === editingCharacterReferenceId.value ? selected : reference)
      : [...characterReferences.value, selected],
  })
  closeCharacterPicker()
}

function selectProductReference(item) {
  if (!editingProductReferenceId.value && totalReferenceCount.value >= MAX_STORYBOARD_REFERENCES) return closeProductPicker()
  const remaining = productReferences.value.filter((reference) => reference.id !== editingProductReferenceId.value)
  if (remaining.some((reference) => reference.id === item.id)) return closeProductPicker()
  const selected = { id: item.id, name: item.name, url: item.url }
  updateData({
    productReferences: editingProductReferenceId.value
      ? productReferences.value.map((reference) => reference.id === editingProductReferenceId.value ? selected : reference)
      : [...productReferences.value, selected].slice(0, productLimit.value),
  })
  closeProductPicker()
}

function removeProductReference(id) {
  updateData({ productReferences: productReferences.value.filter((reference) => reference.id !== id) })
}

function openProductPicker(id = '') {
  editingProductReferenceId.value = id
  productPickerOpen.value = true
}

function openCharacterPicker(id = '') {
  editingCharacterReferenceId.value = id
  const reference = characterReferences.value.find((item) => item.id === id)
  pendingCharacterAsset.value = reference?.pickerKind === 'asset'
    ? { ...reference, mediaType: reference.mediaType || 'image', assetId: reference.assetId || reference.id, pickerKind: 'asset' }
    : null
  characterPickerOpen.value = true
}

function closeCharacterPicker() {
  editingCharacterReferenceId.value = ''
  characterPickerOpen.value = false
  characterAssetPickerOpen.value = false
  pendingCharacterAsset.value = null
}

function openCharacterAssetPicker() {
  characterAssetPickerOpen.value = true
}

function selectCharacterAsset(item) {
  pendingCharacterAsset.value = { ...item, mediaType: item.mediaType || 'image', pickerKind: 'asset' }
  characterAssetPickerOpen.value = false
}

function closeProductPicker() {
  editingProductReferenceId.value = ''
  productPickerOpen.value = false
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: t('canvas.regenerateNamedPlan', { p0: canvasTemplateText(selectedTemplateOption.value.id, selectedTemplateOption.value.label) }),
    message: t('canvas.replaceStoryboardChain', { p0: canvasTemplateText(selectedTemplateOption.value.id, selectedTemplateOption.value.label) }),
    confirmText: t('canvas.continueGeneration'),
  })) return
  if (existingGeneratedNodes.value.length) store.deleteGeneratedNodes(existingGeneratedNodes.value)

  updateNodeData(props.nodeId, {
    templateKey: template.value.key,
    templateId: selectedTemplateOption.value.id,
    templateVersion: template.value.version,
  })
  await runTextTask(streamReversePrompt, buildProductStoryboardRequest({
    workspaceId: store.workspaceId,
    nodeId: props.nodeId,
    model: selectedTextModel.value.id,
    template: template.value,
    productContext: productContext.value,
    duration: props.data.duration,
    videoAspectRatio: props.data.videoAspectRatio,
    characterReferences: characterReferences.value,
    productReferences: productReferences.value,
    userRequirement: props.data.prompt,
  }), {
    failureMessage: t('canvas.namedPlanFailed', { p0: canvasTemplateText(selectedTemplateOption.value.id, selectedTemplateOption.value.label) }),
    onSuccess: (content) => {
      const plan = parseProductStoryboardPlan(content, template.value)
      const generatedNodeIds = store.addProductStoryboardNodes(
        props.nodeId,
        productNode.value.id,
        plan,
        { model: capabilityStore.defaultImageModel.id, aspectRatio: recommended.value.aspectRatio, resolution: recommended.value.resolution },
      )
      return { generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds] }
    },
  })
}
</script>

<template>
  <section class="generation-panel product-visual-panel storyboard-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Clapperboard :size="16" />{{ t('canvas.productStoryboard') }}</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>

    <section class="storyboard-reference-section">
      <header class="storyboard-section-header"><span><Images :size="14" />{{ t('canvas.referenceMedia') }}</span></header>
      <div class="storyboard-reference-row">
        <div class="storyboard-reference-label"><UserRound :size="14" /><span><strong>{{ t('canvas.onScreenCharacters') }}</strong><small>{{ t('canvas.optionalReferenceCount', { p0: characterReferences.length, p1: MAX_STORYBOARD_CHARACTERS, p2: totalReferenceCount, p3: MAX_STORYBOARD_REFERENCES }) }}</small></span></div>
        <div class="storyboard-reference-list">
          <div v-for="(character, index) in characterReferences" :key="character.id" class="storyboard-reference-item">
            <AppButton class="storyboard-reference-main" :title="t('canvas.replaceCharacter', { p0: index + 1, p1: character.name })" :aria-label="t('canvas.replaceCharacter', { p0: index + 1, p1: character.name })" @click="openCharacterPicker(character.id)">
              <AppImageHoverPreview :src="character.url" :preview-src="buildOssImageUrl(character.url, { width: 1200, quality: 90 })" :alt="character.name">
                <img :src="buildOssImageUrl(character.url, { width: 120, quality: 80 })" :alt="character.name" referrerpolicy="no-referrer" />
              </AppImageHoverPreview>
            </AppButton>
            <AppButton class="storyboard-reference-remove" icon-only size="sm" :title="t('canvas.removeCharacter', { p0: index + 1 })" @click="updateData({ characterReferences: characterReferences.filter((reference) => reference.id !== character.id) })"><X :size="13" /></AppButton>
          </div>
          <AppButton v-if="characterReferences.length < MAX_STORYBOARD_CHARACTERS && totalReferenceCount < MAX_STORYBOARD_REFERENCES" class="storyboard-reference-add" variant="soft" @click="openCharacterPicker()"><UserRound :size="14" />{{ t('canvas.addCharacter') }}</AppButton>
        </div>
      </div>
      <div class="storyboard-reference-row">
        <div class="storyboard-reference-label"><Package :size="14" /><span><strong>{{ t('canvas.productReference') }}</strong><small>{{ t('canvas.requiredReferenceCount', { p0: productReferences.length, p1: productLimit, p2: totalReferenceCount, p3: MAX_STORYBOARD_REFERENCES }) }}</small></span></div>
        <div class="storyboard-reference-list">
          <div v-for="reference in productReferences" :key="reference.id" class="storyboard-reference-item">
            <AppButton class="storyboard-reference-main" :title="t('canvas.replaceNamed', { p0: reference.name })" :aria-label="t('canvas.replaceNamed', { p0: reference.name })" @click="openProductPicker(reference.id)">
              <AppImageHoverPreview :src="reference.url" :preview-src="buildOssImageUrl(reference.url, { width: 1200, quality: 90 })" :alt="reference.name">
                <img :src="buildOssImageUrl(reference.url, { width: 120, quality: 80 })" :alt="reference.name" referrerpolicy="no-referrer" />
              </AppImageHoverPreview>
            </AppButton>
            <AppButton class="storyboard-reference-remove" icon-only size="sm" :title="t('canvas.removeNamed', { p0: reference.name })" @click="removeProductReference(reference.id)"><X :size="13" /></AppButton>
          </div>
          <AppButton v-if="productReferences.length < productLimit && totalReferenceCount < MAX_STORYBOARD_REFERENCES" class="storyboard-reference-add" variant="soft" @click="openProductPicker()"><ImagePlus :size="14" />{{ t('canvas.addProductImage') }}</AppButton>
        </div>
      </div>
    </section>

    <section class="storyboard-template-section">
      <header class="storyboard-section-header"><span><Clapperboard :size="14" />{{ t('canvas.contentType') }}</span><small>{{ t('canvas.generationDirection') }}</small></header>
      <div class="storyboard-template-grid">
        <label v-for="option in storyboardTemplates" :key="option.key" class="storyboard-template-option" :class="{ active: option.key === selectedTemplateOption?.key }">
          <input type="radio" name="storyboard-template" :checked="option.key === selectedTemplateOption?.key" @change="selectTemplate(option)" />
          <span><strong>{{ canvasTemplateText(option.id, option.label) }}</strong><small>{{ canvasTemplateText(option.id, option.description, 'description') }}</small></span>
        </label>
      </div>
    </section>

    <div class="storyboard-settings">
      <label><span>{{ t('canvas.totalVideoDuration') }}</span><AppSelect :model-value="data.duration" :options="storyboardDurations.map((value) => ({ value, label: t('canvas.seconds', { p0: value }) }))" :aria-label="t('canvas.totalVideoDuration')" @update:model-value="updateData({ duration: $event })" /></label>
      <label><span>{{ t('canvas.videoRatio') }}</span><AppSelect :model-value="data.videoAspectRatio" :options="ratioOptions" :aria-label="t('canvas.videoRatio')" @update:model-value="updateData({ videoAspectRatio: $event })" /></label>
      <div class="storyboard-recommendation"><Clapperboard :size="14" />{{ t('canvas.storyboardRecommendation', { p0: segmentCount, p1: shots, p2: recommended.aspectRatio, p3: recommended.resolution }) }}</div>
    </div>

    <AppTextarea
      class="storyboard-extra-input nodrag nopan"
      :model-value="data.prompt"
      maxlength="600"
      :placeholder="t('canvas.storyboardPlaceholder')"
      @input="updateData({ prompt: $event.target.value })"
    />

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" :aria-label="t('canvas.textModel')" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />{{ t('canvas.creditCost', { p0: estimatedCredits }) }}</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? t('canvas.generating') : t('canvas.generateProductStoryboard')" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
    <AppAssetPickerModal
      v-if="productPickerOpen"
      resource-type="asset"
      media-type="image"
      :workspace-id="store.workspaceId"
      :node-id="nodeId"
      :selected-url="productReferences.find((reference) => reference.id === editingProductReferenceId)?.url || ''"
      @close="closeProductPicker"
      @select="selectProductReference"
    />
    <AppAssetPickerModal
      v-if="characterPickerOpen"
      resource-type="character"
      include-asset-library
      :workspace-id="store.workspaceId"
      :node-id="nodeId"
      :selected-url="characterReferences.find((reference) => reference.id === editingCharacterReferenceId)?.url || ''"
      :extra-item="pendingCharacterAsset"
      @close="closeCharacterPicker"
      @open-asset-library="openCharacterAssetPicker"
      @select="selectCharacter"
    />
    <AppAssetPickerModal
      v-if="characterAssetPickerOpen"
      resource-type="asset"
      media-type="image"
      :workspace-id="store.workspaceId"
      :node-id="nodeId"
      :selected-url="characterReferences.find((reference) => reference.id === editingCharacterReferenceId)?.url || ''"
      @close="characterAssetPickerOpen = false"
      @select="selectCharacterAsset"
    />
  </section>
</template>
