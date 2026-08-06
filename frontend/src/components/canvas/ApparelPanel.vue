<script setup>
import { computed } from 'vue'
import { ArrowUp, Coins, FileText, Image, LoaderCircle, Plus, Shirt, Trash2 } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { streamReversePrompt } from '../../api/reversals'
import { createEmptyApparelItem, parseApparelProfile } from '../../config/canvas/apparel'
import { defaultReverseModel, reverseModels } from '../../config/reverseModels'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import { useStreamingTextTask } from '../../composables/useStreamingTextTask'
import { useAuthStore } from '../../stores/auth'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppInput from '../ui/AppInput.vue'
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
const { failure, runTextTask } = useStreamingTextTask(props.nodeId)
const reference = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'image'))
const items = computed(() => props.data.items || [])
const selectedModel = computed(() => reverseModels.find((model) => model.id === props.data.model) || defaultReverseModel)
const modelOptions = reverseModels.map(({ id, label }) => ({ value: id, label }))
const compositionOptions = [{ value: 'single', label: '单件服饰' }, { value: 'set', label: '整套搭配' }]
const running = computed(() => props.data.status === 'generating')
const estimatedCredits = computed(() => authStore.estimateCredits('text', selectedModel.value.id))
const insufficientCredits = computed(() => (authStore.user?.credit_balance || 0) < estimatedCredits.value)
const message = computed(() => failure.value || props.data.generationError || (!reference.value?.data.asset
  ? '请先上传服饰参考图'
  : insufficientCredits.value ? `积分不足，本次需要 ${estimatedCredits.value} 积分` : ''))
const canSubmit = computed(() => !running.value && reference.value?.data.asset && !insufficientCredits.value)

function updateData(value) {
  failure.value = ''
  updateNodeData(props.nodeId, { ...value, status: 'ready', generationError: '' })
}

function updateItem(id, value) {
  updateData({ items: items.value.map((item) => item.id === id ? { ...item, ...value } : item) })
}

function addItem() {
  updateData({ items: [...items.value, createEmptyApparelItem()], compositionType: items.value.length ? 'set' : props.data.compositionType })
}

function removeItem(id) {
  const nextItems = items.value.filter((item) => item.id !== id)
  updateData({ items: nextItems, compositionType: nextItems.length > 1 ? 'set' : 'single' })
}

async function submitTask() {
  if (!canSubmit.value) return
  if (items.value.length && !await confirm({
    title: '重新识别服饰资料',
    message: '当前单品清单将被新的识别结果替换。',
    confirmText: '重新识别',
  })) return

  await runTextTask(streamReversePrompt, {
    workspace_id: store.workspaceId,
    node_id: props.nodeId,
    model: selectedModel.value.id,
    media_type: 'image',
    media_url: reference.value.data.asset,
    prompt: props.data.prompt || '',
    response_mode: 'apparel_profile',
  }, {
    failureMessage: '服饰资料识别失败',
    onSuccess: parseApparelProfile,
  })
}

defineExpose({ submitTask })
</script>

<template>
  <section class="generation-panel apparel-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Shirt :size="16" />服饰资料</span>
      <small>{{ items.length ? `${items.length} 件单品` : '等待识别' }}</small>
    </header>

    <div class="apparel-profile-head">
      <div class="apparel-reference" :class="{ empty: !reference?.data.asset }">
        <AppImageHoverPreview v-if="reference?.data.asset" :src="reference.data.asset" :preview-src="buildOssImageUrl(reference.data.asset, { width: 1200, quality: 90 })" alt="服饰参考图">
          <img :src="buildOssImageUrl(reference.data.asset, { width: 220, quality: 82 })" alt="服饰参考图" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <Image v-else :size="22" />
      </div>
      <label><span>资料类型</span><AppSelect :model-value="data.compositionType" :options="compositionOptions" aria-label="服饰资料类型" @update:model-value="updateData({ compositionType: $event })" /></label>
      <label><span>整体搭配摘要</span><AppInput :model-value="data.summary" maxlength="240" placeholder="风格、配色与适用场景" @input="updateData({ summary: $event.target.value })" /></label>
    </div>

    <section class="apparel-items-section">
      <div class="apparel-section-title"><span>单品清单</span><AppButton variant="soft" @click="addItem"><Plus :size="14" />添加单品</AppButton></div>
      <div class="apparel-items">
        <article v-for="(item, index) in items" :key="item.id" class="apparel-item">
          <div class="apparel-item-head">
            <input type="checkbox" :checked="item.enabled" :aria-label="`使用单品${index + 1}`" @change="updateItem(item.id, { enabled: $event.target.checked })" />
            <span>单品 {{ index + 1 }}</span>
            <AppInput :model-value="item.name" aria-label="单品名称" placeholder="单品名称" @input="updateItem(item.id, { name: $event.target.value })" />
            <AppInput :model-value="item.category" aria-label="单品品类" placeholder="品类" @input="updateItem(item.id, { category: $event.target.value })" />
            <AppButton icon-only variant="ghost" :aria-label="`删除单品${index + 1}`" @click="removeItem(item.id)"><Trash2 :size="14" /></AppButton>
          </div>
          <div class="apparel-item-fields">
            <label><span>颜色</span><AppInput :model-value="item.color" placeholder="主色与辅色" @input="updateItem(item.id, { color: $event.target.value })" /></label>
            <label><span>面料</span><AppInput :model-value="item.material" placeholder="可确认的材质" @input="updateItem(item.id, { material: $event.target.value })" /></label>
            <label><span>版型</span><AppInput :model-value="item.silhouette" placeholder="长度与轮廓" @input="updateItem(item.id, { silhouette: $event.target.value })" /></label>
            <label><span>设计细节</span><AppInput :model-value="item.details" placeholder="领型、袖型、图案、工艺" @input="updateItem(item.id, { details: $event.target.value })" /></label>
          </div>
        </article>
        <p v-if="!items.length" class="apparel-empty">上传图片后执行 AI 识别，或手动添加单品。</p>
      </div>
    </section>

    <AppTextarea class="apparel-extra" :model-value="data.prompt" rows="2" maxlength="600" placeholder="补充识别重点，例如：重点区分套装中的配饰与鞋履" @input="updateData({ prompt: $event.target.value })" />
    <p v-if="message" class="panel-notice">{{ message }}</p>
    <footer class="product-visual-panel-footer">
      <FileText :size="16" />
      <AppSelect :model-value="selectedModel.id" :options="modelOptions" aria-label="文本模型" @update:model-value="updateData({ model: $event })" />
      <span class="panel-divider"></span>
      <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
      <AppButton class="run-task-button" icon-only variant="primary" :disabled="!canSubmit" :title="running ? '识别中' : '识别服饰资料'" @click="submitTask">
        <LoaderCircle v-if="running" class="run-task-spinner" :size="18" />
        <ArrowUp v-else :size="18" />
      </AppButton>
    </footer>
  </section>
</template>
