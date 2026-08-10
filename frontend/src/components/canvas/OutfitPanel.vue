<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowUp, Coins, FileText, Image, LoaderCircle, MapPin, Shirt, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { apparelPromptContext } from '../../config/canvas/apparel'
import { resolveOutfitReference } from '../../config/canvas/outfit'
import { buildApparelVideoRequest, buildApparelVisualRequest, parseOutfitPrompt } from '../../config/canvas/outfit'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppSelect from '../ui/AppSelect.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import AppAssetPickerModal from '../assets/AppAssetPickerModal.vue'

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

const apparelNode = computed(() => store.incomingNodeByHandle(props.nodeId, 'apparel'))
const garmentNode = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image' && node.data.asset))
const apparelContext = computed(() => apparelPromptContext(apparelNode.value?.data))
const template = computed(() => contentTemplateStore.templates?.apparel_visual)
const videoTemplate = computed(() => contentTemplateStore.templates?.apparel_showcase)
const templateEnabled = computed(() => Boolean(template.value?.enabled))
const videoTemplateEnabled = computed(() => Boolean(videoTemplate.value?.enabled))
const selectedImageSettings = computed(() => ({ model: { id: 'gpt-image-2' }, aspectRatio: '9:16', resolution: '1K' }))
const selectedTextModel = computed(() => capabilityStore.textModels.find((model) => model.id === props.data.textModel) || capabilityStore.defaultTextModel)
const customRequirement = computed(() => props.data.customRequirement || '')
const running = computed(() => props.data.status === 'generating')
const videoGenerating = ref(false)
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const outfitReference = computed(() => resolveOutfitReference(props.data, store.nodes))
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const modelPickerOpen = ref(false)
const scenePickerOpen = ref(false)
const textModelOptions = computed(() => capabilityStore.textModels.map(({ id, label }) => ({ value: id, label })))
const message = computed(() => {
  if (failure.value || props.data.generationError) return failure.value || props.data.generationError
  if (!templateEnabled.value) return '服饰定妆图模板已停用'
  if (!apparelNode.value) return '请先连接服饰识别节点'
  if (!garmentNode.value?.data.asset) return '请先上传服饰参考图'
  if (!apparelContext.value) return '请先完成服饰识别并启用至少一件单品'
  return insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''
})
const canSubmit = computed(() => templateEnabled.value && !running.value && garmentNode.value?.data.asset && apparelContext.value && !insufficientCredits.value)
const canCreateVideo = computed(() => outfitReference.value.asset && !videoGenerating.value && videoTemplateEnabled.value)
const existingVideoNode = computed(() => props.data.videoNodeId && store.nodes.find((node) => node.id === props.data.videoNodeId))
const sourceItems = computed(() => [
  { label: '服饰识别', icon: Shirt, asset: garmentNode.value?.data.asset, title: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '尚未连接' },
  { label: '模特', icon: UserRound, asset: props.data.modelReference?.url, title: props.data.modelReference?.name || (props.data.modelDescription ? '文字生成/默认模特' : '系统自动生成') },
  { label: '场景', icon: MapPin, asset: props.data.sceneReference?.url, title: props.data.sceneReference?.name || (props.data.sceneDescription ? '文字生成/默认场景' : '系统自动生成') },
])

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function selectReference(kind, item) {
  updateData({
    [`${kind}Source`]: 'library',
    [`${kind}Reference`]: { id: item.id, name: item.name, url: item.url, metadata: item.metadata || {} },
    [`${kind}Description`]: '',
  })
  if (kind === 'model') modelPickerOpen.value = false
  else scenePickerOpen.value = false
}

async function createVideoNode() {
  const reference = outfitReference.value
  if (!reference.asset || !garmentNode.value?.data.asset || videoGenerating.value || !videoTemplateEnabled.value) return
  if (existingVideoNode.value) {
    store.selectNodes([existingVideoNode.value.id])
    return
  }
  videoGenerating.value = true
  try {
    await runTextTask(streamReversePrompt, buildApparelVideoRequest({
      workspaceId: store.workspaceId,
      nodeId: props.nodeId,
      model: selectedTextModel.value.id,
      outfitReferenceUrl: reference.asset,
      garmentUrl: garmentNode.value.data.asset,
      apparelContext: apparelContext.value,
      aspectRatio: props.data.videoAspectRatio || '9:16',
      duration: Number(props.data.duration) || 15,
      templateVersion: videoTemplate.value?.version,
      modelDescription: props.data.modelDescription || undefined,
      sceneDescription: props.data.sceneDescription || undefined,
      userRequirement: props.data.prompt,
    }), {
      failureMessage: '服饰视频方案生成失败',
      onSuccess: (content) => {
        const prompt = parseOutfitPrompt(content)
        const videoId = store.addOutfitVideoNode(props.nodeId, reference.node?.id, garmentNode.value.id, prompt, {
          videoTemplateKey: 'apparel_showcase',
          videoTemplateVersion: videoTemplate.value?.version,
          aspectRatio: props.data.videoAspectRatio || '9:16',
          duration: Number(props.data.duration) || 15,
          generateAudio: false,
          outfitReferenceOrder: ['定妆图', '服饰原图'],
        })
        updateData({ videoNodeId: videoId, videoPrompt: prompt, outfitReferenceConfirmed: true })
        return { generatedNodeIds: [...(props.data.generatedNodeIds || []), videoId].filter(Boolean) }
      },
    })
  } finally {
    videoGenerating.value = false
  }
}

watch(
  () => props.data.createOutfitVideoRequested,
  async (requested) => {
    if (!requested) return
    updateData({ createOutfitVideoRequested: false })
    await createVideoNode()
  },
  { immediate: true },
)

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成服饰穿搭',
    message: '将创建新的试穿定妆图，已有图片节点继续保留在画布中。',
    confirmText: '继续生成',
  })) return

  updateNodeData(props.nodeId, {
    status: 'generating',
    generationError: '',
    imageModel: selectedImageSettings.value.model.id,
    aspectRatio: selectedImageSettings.value.aspectRatio,
    resolution: selectedImageSettings.value.resolution,
    templateVersion: template.value.version,
    generatedNodeIds: [],
  })
  await runTextTask(streamReversePrompt, buildApparelVisualRequest({
    workspaceId: store.workspaceId,
    nodeId: props.nodeId,
    model: selectedTextModel.value.id,
    garmentUrl: garmentNode.value.data.asset,
    modelUrl: props.data.modelReference?.url,
    sceneUrl: props.data.sceneReference?.url,
    modelDescription: props.data.modelDescription,
    sceneDescription: props.data.sceneDescription,
    apparelContext: apparelContext.value,
    aspectRatio: selectedImageSettings.value.aspectRatio,
    resolution: selectedImageSettings.value.resolution,
    templateVersion: template.value.version,
    userRequirement: customRequirement.value,
  }), {
    failureMessage: '服饰穿搭方案生成失败',
    onSuccess: (content) => {
      const settings = selectedImageSettings.value
      const generatedNodeId = store.addOutfitVisualNode(
        props.nodeId,
        garmentNode.value.id,
        parseOutfitPrompt(content),
        {
          model: settings.model.id,
          aspectRatio: settings.aspectRatio,
          resolution: settings.resolution,
          outfitApparelId: apparelNode.value.id,
          outfitModelReference: props.data.modelReference || null,
          outfitSceneReference: props.data.sceneReference || null,
        },
      )
      return { generatedNodeIds: generatedNodeId ? [generatedNodeId] : [] }
    },
  })
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel outfit-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Shirt :size="16" />服饰穿搭</span>
      <small>1 张定妆图</small>
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

    <section class="outfit-material-section outfit-reference-config">
      <h3><Image :size="14" />试穿定妆图</h3>
      <p>服饰为必填；模特和场景可选。生成一张正面全身定妆图，确认后用于视频。</p>
      <AppTextarea
        :model-value="customRequirement"
        rows="2"
        maxlength="600"
        placeholder="可选：补充背景、光线或模特姿态要求"
        @input="updateData({ customRequirement: $event.target.value })"
      />
    </section>

    <section class="outfit-material-section outfit-reference-config">
      <h3><UserRound :size="14" />模特（可选）</h3>
      <AppButton size="sm" variant="soft" @click="modelPickerOpen = true">选择或上传模特</AppButton>
      <AppTextarea :model-value="data.modelDescription" rows="2" maxlength="600" placeholder="可选：输入模特描述，未填写则由系统按服饰生成" @input="updateData({ modelSource: 'prompt', modelReference: null, modelDescription: $event.target.value })" />
    </section>
    <section class="outfit-material-section outfit-reference-config">
      <h3><MapPin :size="14" />场景（可选）</h3>
      <AppButton size="sm" variant="soft" @click="scenePickerOpen = true">选择或上传场景</AppButton>
      <AppTextarea :model-value="data.sceneDescription" rows="2" maxlength="600" placeholder="可选：输入场景描述，未填写则使用生活化默认场景" @input="updateData({ sceneSource: 'prompt', sceneReference: null, sceneDescription: $event.target.value })" />
    </section>

    <div class="outfit-fixed-settings"><span>GPT Image 2</span><span>9:16</span><span>1K</span></div>

    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedTextModel.id" :options="textModelOptions" aria-label="文本模型" @update:model-value="updateData({ textModel: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
    <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成服饰穿搭'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    <AppButton v-if="outfitReference.asset" variant="soft" :disabled="!canCreateVideo && !existingVideoNode" @click="createVideoNode">{{ existingVideoNode ? '打开服饰视频节点' : videoGenerating ? '准备视频…' : '生成服饰视频节点' }}</AppButton>
    </footer>
    <AppAssetPickerModal v-if="modelPickerOpen" resource-type="model" input-role="model" :selected-url="data.modelReference?.url" @close="modelPickerOpen = false" @select="selectReference('model', $event)" />
    <AppAssetPickerModal v-if="scenePickerOpen" resource-type="scene" input-role="scene" :selected-url="data.sceneReference?.url" @close="scenePickerOpen = false" @select="selectReference('scene', $event)" />
  </section>
</template>
