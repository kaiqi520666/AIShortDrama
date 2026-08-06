<script setup>
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Images, LoaderCircle, Shirt, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { apparelPromptContext } from '../../config/canvas/apparel'
import { buildOutfitPlanPrompt, parseOutfitPlan, resolveOutfitMaterials } from '../../config/canvas/outfit'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'

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

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.nodeId && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const apparelNode = computed(() => inputNode('apparel'))
const garmentNode = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image' && node.data.asset))
const modelNode = computed(() => inputNode('model'))
const apparelContext = computed(() => apparelPromptContext(apparelNode.value?.data))
const selectedImageSettings = computed(() => ({ model: { id: 'gpt-image-2' }, aspectRatio: '9:16', resolution: '1K' }))
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const customRequirement = computed(() => props.data.customRequirement || '')
const selectedMaterials = computed(() => resolveOutfitMaterials())
const prompt = computed(() => buildOutfitPlanPrompt(selectedMaterials.value, customRequirement.value, selectedImageSettings.value, apparelContext.value))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const message = computed(() => {
  if (failure.value || props.data.generationError) return failure.value || props.data.generationError
  if (!apparelNode.value) return '请先连接服饰资料节点'
  if (!garmentNode.value?.data.asset) return '请先上传服饰参考图'
  if (!apparelContext.value) return '请先完成服饰资料识别并启用至少一件单品'
  if (!modelNode.value?.data.asset) return '请先选择模特参考图'
  if (!selectedMaterials.value.length) return '请选择穿搭素材或填写自定义要求'
  return insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''
})
const canSubmit = computed(() => !running.value && garmentNode.value?.data.asset && apparelContext.value && modelNode.value?.data.asset && selectedMaterials.value.length && !insufficientCredits.value)
const sourceItems = computed(() => [
  { label: '服饰资料', icon: Shirt, asset: garmentNode.value?.data.asset, title: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '尚未连接' },
  { label: '模特参考图', icon: UserRound, asset: modelNode.value?.data.asset, title: modelNode.value?.data.title || '尚未选择' },
])

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成穿搭方案',
      message: '将重新生成固定六格参考图，已有图片节点不会删除。',
    confirmText: '继续生成',
  })) return

  updateNodeData(props.nodeId, {
    status: 'generating',
    generationError: '',
    imageModel: 'gpt-image-2',
    aspectRatio: '9:16',
    resolution: '1K',
    moduleIds: selectedMaterials.value.map((item) => item.id),
    generatedNodeIds: [],
    outfitBoardAsset: '',
    outfitBoardAssetId: null,
    outfitBoardSourceKey: '',
    outfitBoardStatus: '',
    outfitBoardError: '',
  })
  await runTextTask(streamReversePrompt, {
    workspace_id: store.workspaceId,
    node_id: props.nodeId,
    model: selectedTextModel.value.id,
    media_type: 'image',
    media_url: garmentNode.value.data.asset,
    media_urls: [modelNode.value.data.asset],
    prompt: prompt.value,
    response_mode: 'product_visual_plan',
  }, {
    failureMessage: '穿搭方案生成失败',
    onSuccess: (content) => {
      const settings = selectedImageSettings.value
      const generatedNodeIds = store.addOutfitVisualNodes(
        props.nodeId,
        garmentNode.value.id,
        modelNode.value.id,
        parseOutfitPlan(content, selectedMaterials.value),
        { model: settings.model.id, aspectRatio: settings.aspectRatio, resolution: settings.resolution, outfitApparelId: apparelNode.value.id },
      )
      return { generatedNodeIds }
    },
  })
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
      <div v-for="item in sourceItems" :key="item.label" class="outfit-panel-reference" :class="{ empty: !item.asset }">
        <AppImageHoverPreview v-if="item.asset" :src="item.asset" :preview-src="buildOssImageUrl(item.asset, { width: 1200, quality: 90 })" :alt="item.label">
          <img :src="buildOssImageUrl(item.asset, { width: 240, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <component :is="item.icon" v-else :size="20" />
        <span><strong>{{ item.label }}</strong><small>{{ item.title }}</small></span>
      </div>
    </div>

    <section class="outfit-material-section outfit-reference-board-config">
      <h3><Images :size="14" />固定六格参考图板</h3>
      <p>自动生成 2×3 竖版参考图，全部完成后供服饰分镜使用。</p>
      <div class="outfit-reference-plan-list">
        <span v-for="(item, index) in selectedMaterials" :key="item.id"><b>{{ index + 1 }}</b>{{ item.label }}</span>
      </div>
      <AppTextarea
        :model-value="customRequirement"
        rows="2"
        maxlength="600"
        placeholder="补充统一风格或场景要求（不改变六格结构）"
        @input="updateData({ customRequirement: $event.target.value })"
      />
    </section>

    <div class="outfit-fixed-settings"><span>GPT Image 2</span><span>9:16</span><span>1K</span></div>

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
