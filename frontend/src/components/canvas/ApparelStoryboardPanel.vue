<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, Images, LoaderCircle } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { apparelPromptContext } from '../../config/canvas/apparel'
import { buildOutfitStoryboardPrompt, outfitStoryboardTemplate, parseOutfitStoryboardPlan, storyboardDurations, videoAspectRatios } from '../../config/canvas/outfitStoryboard'
import { defaultImageModel } from '../../config/imageModels'
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
const outfitNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'outfit'))
const boardUrl = computed(() => outfitNode.value?.data.outfitBoardAsset || '')
const apparelNode = computed(() => outfitNode.value && store.incomingNodes(outfitNode.value.id).find((node) => node.type === 'apparel'))
const apparelContext = computed(() => apparelPromptContext(apparelNode.value?.data))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = videoAspectRatios.map((value) => ({ value, label: value }))
const running = computed(() => props.data.status === 'generating')
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const segmentCount = computed(() => Math.max(1, Number(props.data.duration || 15) / 15))
const message = computed(() => notice.value || props.data.generationError || (!outfitNode.value
  ? '请先连接服饰穿搭节点'
  : !boardUrl.value
    ? '请先完成服饰穿搭总览图'
    : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && Boolean(boardUrl.value) && !insufficientCredits.value)

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成服饰分镜方案',
    message: '将替换当前服饰分镜节点链，已有节点会被移除。',
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
      media_url: boardUrl.value,
      media_urls: [],
      prompt: buildOutfitStoryboardPrompt(apparelContext.value, props.data),
      response_mode: 'product_storyboard_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const plan = parseOutfitStoryboardPlan(content, props.data.duration)
    const generatedNodeIds = store.addOutfitStoryboardNodes(
      props.nodeId,
      outfitNode.value.id,
      plan,
      { model: defaultImageModel.id, aspectRatio: props.data.videoAspectRatio, resolution: '2K' },
    )
    updateNodeData(props.nodeId, { status: 'ready', generationStatus: 'succeeded', generatedNodeIds })
  } catch (error) {
    const messageText = error.message || '服饰分镜方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel product-visual-panel storyboard-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Clapperboard :size="16" />服饰分镜</span>
      <small>{{ segmentCount }} 段 · 每段 6 格</small>
    </header>

    <section class="storyboard-reference-section">
      <header class="storyboard-section-header"><span><Images :size="14" />参考素材</span><small>自动读取</small></header>
      <div class="storyboard-reference-row">
        <div class="storyboard-reference-label"><Images :size="14" /><span><strong>服饰总览图</strong><small>必选 · 1/1</small></span></div>
        <div class="storyboard-reference-list">
          <div v-if="boardUrl" class="storyboard-reference-item">
            <div class="storyboard-reference-main">
              <img :src="buildOssImageUrl(boardUrl, { width: 120, quality: 80 })" alt="服饰穿搭参考总览" referrerpolicy="no-referrer" />
              <strong>2K · 9:16 六格总览</strong>
            </div>
          </div>
          <span v-else class="panel-notice">等待服饰穿搭节点完成总览图</span>
        </div>
      </div>
    </section>

    <section class="storyboard-template-section">
      <header class="storyboard-section-header"><span><Clapperboard :size="14" />脚本模板</span><small>固定</small></header>
      <div class="storyboard-template-grid">
        <div class="storyboard-template-option active"><span><strong>{{ outfitStoryboardTemplate.label }}</strong><small>{{ outfitStoryboardTemplate.description }}</small></span></div>
      </div>
    </section>

    <div class="storyboard-settings">
      <label><span>视频总时长</span><AppSelect :model-value="data.duration" :options="storyboardDurations.map((value) => ({ value, label: `${value} 秒` }))" aria-label="视频总时长" @update:model-value="updateData({ duration: $event })" /></label>
      <label><span>视频比例</span><AppSelect :model-value="data.videoAspectRatio" :options="ratioOptions" aria-label="视频比例" @update:model-value="updateData({ videoAspectRatio: $event })" /></label>
      <div class="storyboard-recommendation"><Clapperboard :size="14" />{{ segmentCount }} 段 · 每段 6 格 · 2K</div>
    </div>

    <AppTextarea :model-value="data.prompt" maxlength="600" placeholder="可选：补充走动节奏、场景氛围或展示重点…" @input="updateData({ prompt: $event.target.value })" />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成服饰分镜方案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
