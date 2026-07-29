<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Coins, FileText, Globe2, Image, Images, LoaderCircle, UserRound } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { buildCharacterVisualPrompt, characterProfileContext, characterReady, characterVisualTypes, parseCharacterVisualPlan } from '../../config/canvas/character'
import { worldPromptContext, worldReady } from '../../config/canvas/drama'
import { imageModels, normalizeImageSettings } from '../../config/imageModels'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  embedded: Boolean,
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

const worldNode = computed(() => inputNode('world'))
const referenceImage = computed(() => inputNode('reference'))
const selectedImageSettings = computed(() => normalizeImageSettings({ model: props.data.imageModel, aspectRatio: props.data.aspectRatio, resolution: props.data.resolution }))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const imageModelOptions = imageModels.map(({ id, label }) => ({ value: id, label }))
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = computed(() => selectedImageSettings.value.model.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedImageSettings.value.model.resolutions.map((value) => ({ value, label: value })))
const message = computed(() => notice.value || props.data.generationError || (!worldReady(worldNode.value?.data.world)
  ? '请先完成世界观创作'
  : !characterReady(props.data.profile)
    ? '请先完成角色档案'
    : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && worldReady(worldNode.value?.data.world) && characterReady(props.data.profile) && !insufficientCredits.value)

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
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
    title: '重新生成角色设定图方案',
    message: '将新增 3 个图片节点，已有节点不会删除。',
    confirmText: '继续生成',
  })) return

  let content = ''
  notice.value = ''
  updateNodeData(props.nodeId, { status: 'generating', generationError: '' })
  const prompt = buildCharacterVisualPrompt(
    worldPromptContext(worldNode.value.data),
    characterProfileContext(props.data.profile),
    props.data,
    Boolean(referenceImage.value?.data.asset),
  )
  const onDelta = (delta) => { content += delta }
  const onMeta = (taskId) => updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
  try {
    if (referenceImage.value?.data.asset) {
      await streamReversePrompt({
        workspace_id: store.workspaceId,
        node_id: props.nodeId,
        model: selectedTextModel.value.id,
        media_type: 'image',
        media_url: referenceImage.value.data.asset,
        prompt,
        response_mode: 'character_visual_plan',
      }, onDelta, onMeta)
    } else {
      await streamTextGeneration({ workspace_id: store.workspaceId, node_id: props.nodeId, model: selectedTextModel.value.id, prompt }, onDelta, onMeta)
    }
    const settings = selectedImageSettings.value
    const generatedNodeIds = store.addCharacterVisualNodes(
      props.nodeId,
      referenceImage.value?.data.asset ? referenceImage.value.id : null,
      parseCharacterVisualPlan(content),
      { model: settings.model.id, aspectRatio: settings.aspectRatio, resolution: settings.resolution },
    )
    updateNodeData(props.nodeId, {
      status: 'ready',
      generationStatus: 'succeeded',
      generatedNodeIds: [...existingGeneratedNodes.value, ...generatedNodeIds],
    })
  } catch (error) {
    const messageText = error.message || '角色设定图方案生成失败'
    notice.value = messageText
    updateNodeData(props.nodeId, { status: 'failed', generationError: messageText })
  } finally {
    await authStore.refreshCredits().catch(() => {})
  }
}
</script>

<template>
  <section class="generation-panel product-visual-panel character-visual-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Images :size="16" />角色设定图</span>
      <small><UserRound :size="13" />{{ data.profile?.name || '未命名角色' }}</small>
    </header>
    <div class="outfit-panel-references character-panel-references">
      <div class="outfit-panel-reference" :class="{ empty: !worldNode }">
        <Globe2 :size="20" />
        <span><strong>世界观</strong><small>{{ worldNode?.data.title || '尚未连接' }}</small></span>
      </div>
      <div class="outfit-panel-reference" :class="{ empty: !referenceImage?.data.asset }">
        <img v-if="referenceImage?.data.asset" :src="buildOssImageUrl(referenceImage.data.asset, { width: 240, quality: 80 })" alt="角色参考图" referrerpolicy="no-referrer" />
        <Image v-else :size="20" />
        <span><strong>角色参考图</strong><small>{{ referenceImage?.data.asset ? referenceImage.data.title : '可选' }}</small></span>
      </div>
    </div>
    <section class="character-visual-types">
      <div v-for="item in characterVisualTypes" :key="item.id" class="product-visual-option active">
        <span>{{ item.label }}</span>
      </div>
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
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成设定图方案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
