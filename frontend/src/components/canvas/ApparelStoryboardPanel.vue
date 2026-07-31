<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, Images, LoaderCircle, Shirt, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { apparelPromptContext } from '../../config/canvas/apparel'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { videoModels } from '../../config/videoModels'
import { buildOutfitStoryboardPrompt, getApparelVideoSettings, parseOutfitStoryboardPlan } from '../../config/canvas/outfitStoryboard'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
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
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const notice = ref('')

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.nodeId && item.targetHandle === handle)
  return store.nodes.find((node) => node.id === edge?.source)
}

const apparelNode = computed(() => inputNode('apparel'))
const garmentNode = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image'))
const modelNode = computed(() => inputNode('model'))
const sceneNode = computed(() => inputNode('scene'))
const apparelContext = computed(() => apparelPromptContext(apparelNode.value?.data))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const selectedVideoSettings = computed(() => getApparelVideoSettings(props.data))
const selectedVideoModel = computed(() => selectedVideoSettings.value.model)
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const videoModelOptions = videoModels.map(({ id, label }) => ({ value: id, label }))
const durationOptions = computed(() => {
  const values = selectedVideoModel.value.durationOptions || Array.from({ length: selectedVideoModel.value.durationMax - selectedVideoModel.value.durationMin + 1 }, (_, index) => selectedVideoModel.value.durationMin + index)
  return values.map((value) => ({ value, label: `${value} 秒` }))
})
const running = computed(() => props.data.status === 'generating')
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const sourceItems = computed(() => [
  { label: '服饰', icon: Shirt, asset: garmentNode.value?.data.asset },
  { label: '模特', icon: UserRound, asset: modelNode.value?.data.asset },
  { label: '场景', icon: Images, asset: sceneNode.value?.data.asset },
])
const connectedSourceCount = computed(() => sourceItems.value.filter((item) => item.asset).length)
const message = computed(() => {
  if (notice.value || props.data.generationError) return notice.value || props.data.generationError
  if (!apparelNode.value) return '请先连接服饰资料节点'
  if (!apparelContext.value) return '请先完成服饰资料识别并启用至少一件单品'
  if (!garmentNode.value?.data.asset) return '请先完成服饰资料的参考图上传'
  if (!modelNode.value?.data.asset) return '请先在角色节点选择或上传图片'
  if (!sceneNode.value?.data.asset) return '请先在场景节点选择或上传图片'
  return insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''
})
const canSubmit = computed(() => !running.value && Boolean(apparelContext.value && garmentNode.value?.data.asset && modelNode.value?.data.asset && sceneNode.value?.data.asset) && !insufficientCredits.value)

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function updateVideoModel(modelId) {
  const next = getApparelVideoSettings({ ...props.data, videoModel: modelId })
  updateData({ videoModel: modelId, duration: next.duration, videoAspectRatio: next.aspectRatio, videoResolution: next.resolution, generateAudio: true })
}

function updateVideoSetting(key, value) {
  const next = getApparelVideoSettings({ ...props.data, [key]: value })
  updateData({
    duration: next.duration,
    videoAspectRatio: next.aspectRatio,
    videoResolution: next.resolution,
    generateAudio: true,
  })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成服饰分镜',
    message: '将删除当前故事板图片和视频节点，重新创建一组结果。',
    confirmText: '继续生成',
  })) return
  if (existingGeneratedNodes.value.length) store.deleteNodes(existingGeneratedNodes.value)

  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '', generatedNodeIds: [] })
  try {
    await streamReversePrompt({
      workspace_id: store.workspaceId,
      node_id: props.nodeId,
      model: selectedTextModel.value.id,
      media_type: 'image',
      media_url: garmentNode.value.data.asset,
      media_urls: [modelNode.value.data.asset, sceneNode.value.data.asset],
      prompt: buildOutfitStoryboardPrompt(apparelContext.value, props.data),
      response_mode: 'apparel_storyboard_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const plan = parseOutfitStoryboardPlan(content, props.data.duration, props.data)
    const generatedNodeIds = store.addApparelStoryboardNodes(
      props.nodeId,
      garmentNode.value.id,
      modelNode.value.id,
      sceneNode.value.id,
      plan,
      { imageSettings: plan.imageSettings, videoSettings: plan.videoSettings },
    )
    if (generatedNodeIds.length !== 2) throw new Error('故事板节点创建失败')
    updateNodeData(props.nodeId, { status: 'ready', generationStatus: 'succeeded', generatedNodeIds })
  } catch (error) {
    const messageText = error.response?.data?.message || error.message || '服饰分镜方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel product-visual-panel storyboard-panel apparel-storyboard-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Clapperboard :size="16" />服饰分镜</span>
    </header>

    <section class="storyboard-reference-section apparel-storyboard-reference-section">
      <header class="storyboard-section-header"><span><Images :size="14" />参考素材</span><small>{{ connectedSourceCount }}/3 已连接</small></header>
      <div v-for="item in sourceItems" :key="item.label" class="storyboard-reference-row">
        <div class="storyboard-reference-label"><component :is="item.icon" :size="14" /><span><strong>{{ item.label }}</strong></span></div>
        <div class="storyboard-reference-list">
          <div class="storyboard-reference-item apparel-storyboard-reference-item" :class="{ empty: !item.asset }">
            <AppImageHoverPreview v-if="item.asset" :src="item.asset" :preview-src="buildOssImageUrl(item.asset, { width: 1200, quality: 90 })" :alt="item.label">
              <img :src="buildOssImageUrl(item.asset, { width: 120, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
            </AppImageHoverPreview>
            <component :is="item.icon" v-else :size="16" />
            <strong v-if="!item.asset">待连接</strong>
          </div>
        </div>
      </div>
    </section>

    <div class="storyboard-settings apparel-storyboard-settings">
      <label><span>视频时长</span><AppSelect :model-value="selectedVideoSettings.duration" :options="durationOptions" aria-label="视频时长" @update:model-value="updateVideoSetting('duration', $event)" /></label>
      <label><span>视频模型</span><AppSelect :model-value="selectedVideoModel.id" :options="videoModelOptions" aria-label="视频模型" @update:model-value="updateVideoModel" /></label>
      <label><span>视频比例</span><AppSelect :model-value="selectedVideoSettings.aspectRatio" :options="selectedVideoModel.aspectRatios.map((value) => ({ value, label: value }))" aria-label="视频比例" @update:model-value="updateVideoSetting('videoAspectRatio', $event)" /></label>
    </div>

    <AppTextarea :model-value="data.prompt" maxlength="600" placeholder="补充要求（可选）" aria-label="补充要求" @input="updateData({ prompt: $event.target.value })" />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成服饰分镜'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
