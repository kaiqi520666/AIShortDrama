<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Coins, FileText, Images, LoaderCircle, Shirt, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { buildOutfitPlanPrompt, outfitMaterialGroups, parseOutfitPlan, resolveOutfitMaterials } from '../../config/canvas/outfit'
import { imageModels, normalizeImageSettings } from '../../config/imageModels'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
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

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.nodeId && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const garmentNode = computed(() => inputNode('garment'))
const modelNode = computed(() => inputNode('model'))
const selectedImageSettings = computed(() => normalizeImageSettings({
  model: props.data.imageModel,
  aspectRatio: props.data.aspectRatio,
  resolution: props.data.resolution,
}))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const customRequirement = computed(() => props.data.customRequirement ?? props.data.customScene ?? '')
const selectedMaterials = computed(() => resolveOutfitMaterials(props.data.moduleIds, props.data.sceneIds, customRequirement.value))
const selectedMaterialIds = computed(() => selectedMaterials.value.map((item) => item.id))
const prompt = computed(() => buildOutfitPlanPrompt(selectedMaterials.value, customRequirement.value, props.data))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const imageModelOptions = imageModels.map(({ id, label }) => ({ value: id, label }))
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = computed(() => selectedImageSettings.value.model.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedImageSettings.value.model.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => notice.value || props.data.generationError || (!garmentNode.value?.data.asset
  ? '请先选择服饰参考图'
  : !modelNode.value?.data.asset
    ? '请先选择模特参考图'
    : !selectedMaterials.value.length
      ? '请选择穿搭素材或填写自定义要求'
      : insufficientCredits.value
        ? `积分不足，本次需要 ${estimatedCredits.value} 积分`
        : ''))
const canSubmit = computed(() => !running.value && garmentNode.value?.data.asset && modelNode.value?.data.asset && selectedMaterials.value.length && !insufficientCredits.value)
const sourceItems = computed(() => [
  { label: '服饰参考图', icon: Shirt, node: garmentNode.value },
  { label: '模特参考图', icon: UserRound, node: modelNode.value },
])

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function toggleMaterial(id) {
  const moduleIds = selectedMaterialIds.value.filter((value) => value !== 'custom')
  updateData({ moduleIds: moduleIds.includes(id) ? moduleIds.filter((value) => value !== id) : [...moduleIds, id] })
}

function updateImageModel(imageModel) {
  const model = imageModels.find(({ id }) => id === imageModel)
  updateData({
    imageModel: model.id,
    aspectRatio: model.aspectRatios.includes(props.data.aspectRatio) ? props.data.aspectRatio : model.defaultAspectRatio,
    resolution: model.resolutions.includes(props.data.resolution) ? props.data.resolution : model.defaultResolution,
  })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成穿搭方案',
    message: `将新增 ${selectedMaterials.value.length} 个穿搭素材节点，已有节点不会删除。`,
    confirmText: '继续生成',
  })) return

  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  try {
    await streamReversePrompt({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: selectedTextModel.value.id,
      media_type: 'image',
      media_url: garmentNode.value.data.asset,
      media_urls: [modelNode.value.data.asset],
      prompt: prompt.value,
      response_mode: 'product_visual_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const settings = selectedImageSettings.value
    const plans = parseOutfitPlan(content, selectedMaterials.value)
    const generatedNodeIds = store.addOutfitVisualNodes(
      props.nodeId,
      garmentNode.value.id,
      modelNode.value.id,
      plans,
      { model: settings.model.id, aspectRatio: settings.aspectRatio, resolution: settings.resolution },
    )
    updateNodeData(props.nodeId, {
      status: 'ready',
      generationStatus: 'succeeded',
      generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds],
    })
  } catch (error) {
    const messageText = error.response?.data?.message || error.message || '穿搭方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel outfit-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Shirt :size="16" />穿搭素材</span>
      <small>已选 {{ selectedMaterials.length }} 项</small>
    </header>

    <div class="outfit-panel-references">
      <div v-for="item in sourceItems" :key="item.label" class="outfit-panel-reference" :class="{ empty: !item.node?.data.asset }">
        <img v-if="item.node?.data.asset" :src="buildOssImageUrl(item.node.data.asset, { width: 240, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
        <component :is="item.icon" v-else :size="20" />
        <span><strong>{{ item.label }}</strong><small>{{ item.node?.data.asset ? item.node.data.title : '尚未选择' }}</small></span>
      </div>
    </div>

    <section class="outfit-material-section">
      <h3><Images :size="14" />选择要生成的素材</h3>
      <div v-for="group in outfitMaterialGroups" :key="group.id" class="outfit-material-group">
        <span>{{ group.label }}</span>
        <div class="outfit-material-options">
          <label v-for="item in group.items" :key="item.id" class="product-visual-option" :class="{ active: selectedMaterialIds.includes(item.id) }" :title="item.description">
            <input type="checkbox" :checked="selectedMaterialIds.includes(item.id)" @change="toggleMaterial(item.id)" />
            <span>{{ item.label }}</span>
          </label>
        </div>
      </div>
      <AppTextarea
        :model-value="customRequirement"
        rows="2"
        maxlength="600"
        placeholder="补充场景、风格或展示要求；未选预设时将单独生成自定义素材"
        @input="updateData({ customRequirement: $event.target.value })"
      />
    </section>

    <div class="product-visual-settings">
      <label><span>图片模型</span><AppSelect :model-value="selectedImageSettings.model.id" :options="imageModelOptions" aria-label="图片模型" @update:model-value="updateImageModel" /></label>
      <label><span>画面比例</span><AppSelect :model-value="selectedImageSettings.aspectRatio" :options="ratioOptions" aria-label="画面比例" @update:model-value="updateData({ aspectRatio: $event })" /></label>
      <label><span>清晰度</span><AppSelect :model-value="selectedImageSettings.resolution" :options="resolutionOptions" aria-label="清晰度" @update:model-value="updateData({ resolution: $event })" /></label>
    </div>

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成穿搭素材'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
