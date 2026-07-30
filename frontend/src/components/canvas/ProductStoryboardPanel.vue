<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, ImagePlus, Images, LoaderCircle, Package, UserRound, X } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { productPromptContext } from '../../config/canvas/ecommerce'
import {
  buildProductStoryboardPrompt,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
  storyboardDurations,
  storyboardSegmentCount,
  storyboardShotCount,
  videoAspectRatios,
} from '../../config/canvas/productStoryboard'
import { defaultImageModel } from '../../config/imageModels'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppAssetPickerModal from '../assets/AppAssetPickerModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const notice = ref('')
const characterPickerOpen = ref(false)
const productPickerOpen = ref(false)
const editingProductReferenceId = ref('')
const productNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const productReferences = computed(() => Array.isArray(props.data.productReferences) ? props.data.productReferences : [])
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const selectedTemplates = computed(() => (props.data.templates || []).filter((item) => item.enabled))
const selectedTemplate = computed(() => selectedTemplates.value[0] || null)
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const segmentCount = computed(() => storyboardSegmentCount(props.data.duration))
const shots = computed(() => storyboardShotCount(15))
const recommended = computed(() => recommendStoryboardSettings(15, props.data.videoAspectRatio, defaultImageModel))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = videoAspectRatios.map((value) => ({ value, label: value }))
const character = computed(() => props.data.characterReference || null)
const message = computed(() => notice.value || props.data.generationError || (!productNode.value
  ? '请先连接商品创作节点'
  : !productReferences.value.length
    ? '请先选择商品参考图'
    : !productContext.value
      ? '请先完成商品识别'
      : !selectedTemplate.value
        ? '请选择一个脚本模板'
        : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && productNode.value && productReferences.value.length && productContext.value && selectedTemplate.value && !insufficientCredits.value)

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function updateTemplate(id) {
  updateData({
    templateId: id,
    templates: props.data.templates.map((item) => ({ ...item, enabled: item.id === id })),
  })
}

function selectCharacter(item) {
  updateData({
    characterReference: {
      id: item.id,
      name: item.name,
      url: item.url,
      assetUrl: item.seedanceAssetUrl,
      groupId: item.seedanceGroupId,
    },
  })
  characterPickerOpen.value = false
}

function selectProductReference(item) {
  const remaining = productReferences.value.filter((reference) => reference.id !== editingProductReferenceId.value)
  if (remaining.some((reference) => reference.id === item.id)) return closeProductPicker()
  const selected = { id: item.id, name: item.name, url: item.url }
  updateData({
    productReferences: editingProductReferenceId.value
      ? productReferences.value.map((reference) => reference.id === editingProductReferenceId.value ? selected : reference)
      : [...productReferences.value, selected].slice(0, 3),
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

function closeProductPicker() {
  editingProductReferenceId.value = ''
  productPickerOpen.value = false
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成商品分镜方案',
    message: '将替换当前分镜链，已有节点会被移除。',
    confirmText: '继续生成',
  })) return
  if (existingGeneratedNodes.value.length) store.deleteNodes(existingGeneratedNodes.value)

  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  try {
    await streamReversePrompt({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: selectedTextModel.value.id,
      media_type: 'image',
      media_url: productReferences.value[0].url,
      media_urls: [
        ...productReferences.value.slice(1).map((reference) => reference.url),
        ...(character.value?.url ? [character.value.url] : []),
      ],
      prompt: buildProductStoryboardPrompt(productContext.value, [selectedTemplate.value], props.data),
      response_mode: 'product_storyboard_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const plan = parseProductStoryboardPlan(content, [selectedTemplate.value], character.value, productReferences.value.length)
    const generatedNodeIds = store.addProductStoryboardNodes(
      props.nodeId,
      productNode.value.id,
      plan,
      { model: defaultImageModel.id, aspectRatio: recommended.value.aspectRatio, resolution: recommended.value.resolution },
    )
    updateNodeData(props.nodeId, {
      status: 'ready',
      generationStatus: 'succeeded',
      generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds],
    })
  } catch (error) {
    const messageText = error.message || '商品分镜方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}
</script>

<template>
  <section class="generation-panel product-visual-panel storyboard-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Clapperboard :size="16" />商品分镜</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>

    <section class="storyboard-reference-section">
      <header class="storyboard-section-header"><span><Images :size="14" />参考素材</span></header>
      <div class="storyboard-reference-row">
        <div class="storyboard-reference-label"><UserRound :size="14" /><span><strong>出镜角色</strong><small>可选 · {{ character ? 1 : 0 }}/1</small></span></div>
        <div class="storyboard-reference-list">
          <div v-if="character" class="storyboard-reference-item">
            <AppButton class="storyboard-reference-main" :title="`更换${character.name}`" @click="characterPickerOpen = true">
              <img :src="buildOssImageUrl(character.url, { width: 120, quality: 80 })" :alt="character.name" referrerpolicy="no-referrer" />
              <strong>{{ character.name }}</strong>
            </AppButton>
            <AppButton class="storyboard-reference-remove" icon-only size="sm" title="移除出镜角色" @click="updateData({ characterReference: null })"><X :size="13" /></AppButton>
          </div>
          <AppButton v-else class="storyboard-reference-add" variant="soft" @click="characterPickerOpen = true"><UserRound :size="14" />选择角色</AppButton>
        </div>
      </div>
      <div class="storyboard-reference-row">
        <div class="storyboard-reference-label"><Package :size="14" /><span><strong>商品参考图</strong><small>必选 · {{ productReferences.length }}/3</small></span></div>
        <div class="storyboard-reference-list">
          <div v-for="reference in productReferences" :key="reference.id" class="storyboard-reference-item">
            <AppButton class="storyboard-reference-main" :title="`更换${reference.name}`" @click="openProductPicker(reference.id)">
              <img :src="buildOssImageUrl(reference.url, { width: 120, quality: 80 })" :alt="reference.name" referrerpolicy="no-referrer" />
              <strong>{{ reference.name }}</strong>
            </AppButton>
            <AppButton class="storyboard-reference-remove" icon-only size="sm" :title="`移除${reference.name}`" @click="removeProductReference(reference.id)"><X :size="13" /></AppButton>
          </div>
          <AppButton v-if="productReferences.length < 3" class="storyboard-reference-add" variant="soft" @click="openProductPicker()"><ImagePlus :size="14" />添加商品图</AppButton>
        </div>
      </div>
    </section>

    <section class="storyboard-template-section">
      <header class="storyboard-section-header"><span><Clapperboard :size="14" />脚本模板</span><small>单选</small></header>
      <div class="storyboard-template-grid">
        <label v-for="item in data.templates" :key="item.id" class="storyboard-template-option" :class="{ active: item.enabled }">
          <input type="radio" name="storyboard-template" :checked="item.enabled" @change="updateTemplate(item.id)" />
          <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
        </label>
      </div>
    </section>

    <div class="storyboard-settings">
      <label><span>视频总时长</span><AppSelect :model-value="data.duration" :options="storyboardDurations.map((value) => ({ value, label: `${value} 秒` }))" aria-label="视频总时长" @update:model-value="updateData({ duration: $event })" /></label>
      <label><span>视频比例</span><AppSelect :model-value="data.videoAspectRatio" :options="ratioOptions" aria-label="视频比例" @update:model-value="updateData({ videoAspectRatio: $event })" /></label>
      <div class="storyboard-recommendation"><Clapperboard :size="14" />{{ segmentCount }} 段 · 每段 {{ shots }} 格 · {{ recommended.aspectRatio }} · {{ recommended.resolution }}</div>
    </div>

    <AppTextarea
      class="storyboard-extra-input nodrag nopan"
      :model-value="data.prompt"
      maxlength="600"
      placeholder="可选：补充节奏、场景、受众或画面要求…"
      @input="updateData({ prompt: $event.target.value })"
    />

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成商品分镜方案'" @click="submitTask">
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
      :workspace-id="store.workspaceId"
      :node-id="nodeId"
      :selected-url="character?.url || ''"
      @close="characterPickerOpen = false"
      @select="selectCharacter"
    />
  </section>
</template>
