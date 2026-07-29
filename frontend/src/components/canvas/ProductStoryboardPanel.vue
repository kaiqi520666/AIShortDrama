<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, Clapperboard, Coins, FileText, LoaderCircle, Package, UserRound, X } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { productPromptContext } from '../../config/canvas/ecommerce'
import {
  buildProductStoryboardPrompt,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
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
const productNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const referenceImage = computed(() => productNode.value && store.incomingNodes(productNode.value.id).find((node) => node.type === 'image' && node.data.asset))
const productContext = computed(() => productPromptContext(productNode.value?.data.product))
const selectedTemplates = computed(() => (props.data.templates || []).filter((item) => item.enabled))
const selectedTextModel = computed(() => reverseModels.find((model) => model.id === props.data.textModel) || defaultReverseModel)
const shots = computed(() => storyboardShotCount(props.data.duration))
const recommended = computed(() => recommendStoryboardSettings(props.data.duration, props.data.videoAspectRatio, defaultImageModel))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedTextModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const existingGeneratedNodes = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)))
const textModelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const ratioOptions = videoAspectRatios.map((value) => ({ value, label: value }))
const character = computed(() => props.data.characterReference || null)
const message = computed(() => notice.value || props.data.generationError || (!productNode.value
  ? '请先连接商品创作节点'
  : !referenceImage.value
    ? '请先上传商品参考图'
    : !productContext.value
      ? '请先完成商品识别'
      : !selectedTemplates.value.length
        ? '至少选择一个脚本模板'
        : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && productNode.value && referenceImage.value && productContext.value && selectedTemplates.value.length && !insufficientCredits.value)

function updateData(value) {
  notice.value = ''
  updateNodeData(props.nodeId, { ...value, generationError: '' })
}

function updateTemplate(id, enabled) {
  updateData({ templates: props.data.templates.map((item) => item.id === id ? { ...item, enabled } : item) })
}

function selectCharacter(item) {
  updateData({
    characterReference: {
      id: item.id,
      name: item.name,
      url: item.url,
      assetUrl: item.seedanceAssetUrl,
    },
  })
  characterPickerOpen.value = false
}

async function submitTask() {
  if (!canSubmit.value) return
  if (existingGeneratedNodes.value.length && !await confirm({
    title: '重新生成商品分镜方案',
    message: `将新增 ${selectedTemplates.value.length} 个分镜板图片节点，已有节点不会删除。`,
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
      media_url: referenceImage.value.data.asset,
      ...(character.value?.url ? { media_urls: [character.value.url] } : {}),
      prompt: buildProductStoryboardPrompt(productContext.value, selectedTemplates.value, props.data),
      response_mode: 'product_storyboard_plan',
    }, (delta) => { content += delta }, (taskId) => {
      updateNodeData(props.nodeId, { generationTaskId: taskId, generationStatus: 'running' })
    })
    const generatedNodeIds = store.addProductStoryboardNodes(
      props.nodeId,
      productNode.value.id,
      referenceImage.value.id,
      parseProductStoryboardPlan(content, selectedTemplates.value, character.value),
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

    <div class="storyboard-character">
      <span><UserRound :size="14" />出镜角色</span>
      <div v-if="character" class="storyboard-character-selected">
        <img :src="buildOssImageUrl(character.url, { width: 120, quality: 80 })" :alt="character.name" referrerpolicy="no-referrer" />
        <strong>{{ character.name }}</strong>
        <AppButton size="sm" variant="soft" @click="characterPickerOpen = true">更换</AppButton>
        <AppButton icon-only size="sm" variant="soft" title="移除出镜角色" @click="updateData({ characterReference: null })"><X :size="14" /></AppButton>
      </div>
      <AppButton v-else size="sm" variant="soft" @click="characterPickerOpen = true"><UserRound :size="14" />无人脸模式 · 选择角色</AppButton>
    </div>

    <div class="storyboard-template-grid">
      <label v-for="item in data.templates" :key="item.id" class="storyboard-template-option" :class="{ active: item.enabled }">
        <input type="checkbox" :checked="item.enabled" @change="updateTemplate(item.id, $event.target.checked)" />
        <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
      </label>
    </div>

    <div class="storyboard-settings">
      <label class="storyboard-duration">
        <span>视频时长 <strong>{{ data.duration }} 秒</strong></span>
        <input type="range" min="4" max="15" step="1" :value="data.duration" @input="updateData({ duration: Number($event.target.value) })" />
      </label>
      <label><span>视频比例</span><AppSelect :model-value="data.videoAspectRatio" :options="ratioOptions" aria-label="视频比例" @update:model-value="updateData({ videoAspectRatio: $event })" /></label>
      <div class="storyboard-recommendation"><Clapperboard :size="14" />预计 {{ shots }} 格 · 分镜板 {{ recommended.aspectRatio }} · {{ recommended.resolution }}</div>
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
