<script setup>
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Globe2, Image, LoaderCircle } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamTextGeneration } from '../../api/generations'
import { streamReversePrompt } from '../../api/reversals'
import { buildCharacterProfilePrompt, mergeCharacterProfile, parseCharacterProfile } from '../../config/canvas/character'
import { worldPromptContext, worldReady } from '../../config/canvas/drama'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
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
  embedded: Boolean,
})

const store = useCanvasStore()
const authStore = useAuthStore()
const { updateNodeData } = useVueFlow()
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.nodeId && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const worldNode = computed(() => inputNode('world'))
const referenceImage = computed(() => inputNode('reference'))
const selectedModel = computed(() => reverseModels.find((model) => model.id === props.data.model) || defaultReverseModel)
const modelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => estimatedCredits.value !== null && (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => failure.value || props.data.generationError || (!worldNode.value
  ? '请先连接世界观创作节点'
  : !worldReady(worldNode.value.data.world)
    ? '请先完成世界观创作'
    : !props.data.prompt?.trim()
      ? '请先输入角色想法'
      : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && worldReady(worldNode.value?.data.world) && props.data.prompt?.trim() && !insufficientCredits.value)

async function submitTask() {
  if (!canSubmit.value) return
  const prompt = buildCharacterProfilePrompt(worldPromptContext(worldNode.value.data), props.data, Boolean(referenceImage.value?.data.asset))
  const hasReference = Boolean(referenceImage.value?.data.asset)
  const streamer = hasReference ? streamReversePrompt : streamTextGeneration
  await runTextTask(streamer, hasReference
    ? {
        workspace_id: store.workspaceId,
        node_id: props.nodeId,
        model: selectedModel.value.id,
        media_type: 'image',
        media_url: referenceImage.value.data.asset,
        prompt,
        response_mode: 'character_profile',
      }
    : { workspace_id: store.workspaceId, node_id: props.nodeId, model: selectedModel.value.id, prompt }, {
    failureMessage: '角色档案生成失败',
    onSuccess: (content) => ({
      profile: mergeCharacterProfile(props.data.profile, parseCharacterProfile(content)),
      workflowStep: 'visual',
    }),
  })
}
</script>

<template>
  <section class="generation-panel character-profile-panel nodrag nowheel" :class="{ embedded }" @pointerdown.stop>
    <div class="reference-strip">
      <div class="reference-item" :class="{ optional: !worldNode }" :title="worldNode ? '世界观' : '世界观（未连接）'">
        <Globe2 :size="20" /><b>{{ worldNode ? 1 : '?' }}</b>
      </div>
      <div v-if="referenceImage?.data.asset" class="reference-item" title="角色参考图">
        <AppImageHoverPreview :src="referenceImage.data.asset" :preview-src="buildOssImageUrl(referenceImage.data.asset, { width: 1200, quality: 90 })" alt="角色参考图">
          <img :src="buildOssImageUrl(referenceImage.data.asset)" alt="角色参考图" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <b>1</b>
      </div>
      <div v-else class="reference-item optional" title="角色参考图（可选）">
        <Image :size="20" /><b>?</b>
      </div>
    </div>
    <AppTextarea
      :model-value="data.prompt"
      maxlength="1200"
      placeholder="输入角色的大概想法，例如：表面冷静、执着追查失踪案的年轻记者……"
      @input="failure = ''; updateNodeData(nodeId, { prompt: $event.target.value, generationError: '' })"
    />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer>
      <FileText :size="16" />
      <AppSelect :model-value="selectedModel.id" :options="modelOptions" aria-label="文本模型" @update:model-value="updateNodeData(nodeId, { model: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '生成中' : '生成角色档案'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
