<script setup>
import { computed } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, Images, LoaderCircle, Shirt } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { apparelPromptContext } from '../../config/canvas/apparel'
import { buildOutfitStoryboardRequest, parseOutfitStoryboardPlan } from '../../config/canvas/outfitStoryboard'
import { recommendStoryboardSettings, storyboardSegmentCount } from '../../config/canvas/productStoryboard'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
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
const contentTemplateStore = useContentTemplatesStore()
const authStore = useAuthStore()
const { confirm } = useGlobalConfirm()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)

const outfitNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'outfit'))
const legacyApparelNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'apparel'))
const apparelNode = computed(() => outfitNode.value && store.incomingNodeByHandle(outfitNode.value.id, 'apparel'))
const garmentNode = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image' && node.data.asset))
const modelNode = computed(() => outfitNode.value && store.incomingNodeByHandle(outfitNode.value.id, 'model'))
const sceneNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'scene'))
const apparelContext = computed(() => apparelPromptContext(apparelNode.value?.data))
const template = computed(() => contentTemplateStore.templates?.apparel_showcase)
const templateEnabled = computed(() => Boolean(template.value?.enabled))
const durations = computed(() => template.value?.config?.durations || [])
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const selectedDuration = computed(() => durations.value.includes(Number(props.data.duration)) ? Number(props.data.duration) : durations.value[0])
const ratioOptions = computed(() => capabilityStore.defaultVideoModel.aspectRatios.map((value) => ({ value, label: value })))
const recommended = computed(() => recommendStoryboardSettings(15, props.data.videoAspectRatio, capabilityStore.defaultImageModel))
const segmentCount = computed(() => storyboardSegmentCount(selectedDuration.value, durations.value))
const running = computed(() => props.data.status === 'generating')
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const sourceItems = computed(() => [
  { label: '模特试穿总览', asset: outfitNode.value?.data.outfitBoardAsset, required: true },
  { label: '场景参考', asset: sceneNode.value?.data.asset, required: false },
])
const message = computed(() => {
  if (failure.value || props.data.generationError) return failure.value || props.data.generationError
  if (!templateEnabled.value) return '服饰展示模板已停用'
  if (!outfitNode.value) return legacyApparelNode.value
    ? '这是旧版服饰分镜，请新建模特试穿节点并连接到试穿输入'
    : '请先连接模特试穿节点'
  if (!outfitNode.value.data.outfitBoardAsset) return '请先完成六视角试穿总览'
  if (!garmentNode.value?.data.asset || !modelNode.value?.data.asset || !apparelContext.value) return '模特试穿的服饰或模特资料不完整'
  return insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''
})
const canSubmit = computed(() => templateEnabled.value && !running.value && outfitNode.value?.data.outfitBoardAsset && garmentNode.value?.data.asset && modelNode.value?.data.asset && apparelContext.value && !insufficientCredits.value)

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成服饰展示',
    message: '将删除当前服饰分镜链，并按新的时长和要求重新创建。',
    confirmText: '继续生成',
  })) return
  if (existingGeneratedNodes.value.length) store.deleteNodes(existingGeneratedNodes.value)

  updateNodeData(props.nodeId, {
    status: 'generating',
    generationError: '',
    templateKey: 'apparel_showcase',
    templateVersion: template.value.version,
    generatedNodeIds: [],
  })
  await runTextTask(streamReversePrompt, buildOutfitStoryboardRequest({
    workspaceId: store.workspaceId,
    nodeId: props.nodeId,
    model: selectedTextModel.value.id,
    template: template.value,
    outfitBoardUrl: outfitNode.value.data.outfitBoardAsset,
    garmentUrl: garmentNode.value.data.asset,
    modelUrl: modelNode.value.data.asset,
    sceneUrl: sceneNode.value?.data.asset,
    apparelContext: apparelContext.value,
    duration: selectedDuration.value,
    videoAspectRatio: props.data.videoAspectRatio,
    userRequirement: props.data.prompt,
  }), {
    failureMessage: '服饰展示方案生成失败',
    onSuccess: (content) => {
      const plan = parseOutfitStoryboardPlan(content, template.value)
      const generatedNodeIds = store.addOutfitStoryboardNodes(
        props.nodeId,
        outfitNode.value.id,
        sceneNode.value?.id,
        plan,
        { model: capabilityStore.defaultImageModel.id, aspectRatio: recommended.value.aspectRatio, resolution: recommended.value.resolution },
      )
      return { generatedNodeIds }
    },
  })
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel product-visual-panel storyboard-panel apparel-storyboard-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Clapperboard :size="16" />服饰分镜</span>
      <small>{{ segmentCount }} 段 · 每段 6 镜头</small>
    </header>

    <section class="storyboard-reference-section apparel-storyboard-reference-section">
      <header class="storyboard-section-header"><span><Images :size="14" />参考素材</span></header>
      <div v-for="item in sourceItems" :key="item.label" class="storyboard-reference-row">
        <div class="storyboard-reference-label"><Shirt :size="14" /><span><strong>{{ item.label }}</strong><small>{{ item.required ? '必选' : '可选' }}</small></span></div>
        <div class="storyboard-reference-list">
          <div class="storyboard-reference-item apparel-storyboard-reference-item" :class="{ empty: !item.asset }">
            <AppImageHoverPreview v-if="item.asset" :src="item.asset" :preview-src="buildOssImageUrl(item.asset, { width: 1200, quality: 90 })" :alt="item.label">
              <img :src="buildOssImageUrl(item.asset, { width: 120, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
            </AppImageHoverPreview>
            <Images v-else :size="16" />
            <strong v-if="!item.asset">{{ item.required ? '待生成' : '未设置' }}</strong>
          </div>
        </div>
      </div>
    </section>

    <div class="storyboard-settings apparel-storyboard-settings">
      <label><span>视频总时长</span><AppSelect :model-value="selectedDuration" :options="durations.map((value) => ({ value, label: `${value} 秒` }))" aria-label="视频总时长" @update:model-value="updateData({ duration: $event })" /></label>
      <label><span>视频比例</span><AppSelect :model-value="data.videoAspectRatio" :options="ratioOptions" aria-label="视频比例" @update:model-value="updateData({ videoAspectRatio: $event })" /></label>
      <div class="storyboard-recommendation"><Clapperboard :size="14" />{{ segmentCount }} 段 · 每段 6 格 · {{ recommended.aspectRatio }} · {{ recommended.resolution }}</div>
    </div>

    <AppTextarea :model-value="data.prompt" maxlength="600" placeholder="可选：补充动作、场景、节奏或展示重点…" aria-label="补充要求" @input="updateData({ prompt: $event.target.value })" />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成服饰展示方案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
