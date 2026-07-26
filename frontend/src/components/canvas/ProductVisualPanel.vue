<script setup>
import { computed } from 'vue'
import { BadgeCheck, Box, Images, Minus, Package, Plus, ScanSearch } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import { getImageModel, imageModels } from '../../config/imageModels'
import { productVisualGroups } from '../../config/canvas/productVisual'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'
import AppSelect from '../ui/AppSelect.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
})

const groupIcons = { basic: Box, marketing: BadgeCheck, detail: ScanSearch, trust: Package }
const store = useCanvasStore()
const { updateNodeData } = useVueFlow()
const productNode = computed(() => store.incomingNodes(props.nodeId).find((node) => node.type === 'product'))
const selectedModel = computed(() => getImageModel(props.data.model))
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
const totalCount = computed(() => selectedItems.value.reduce((sum, item) => sum + item.count, 0))
const modelOptions = imageModels.map((model) => ({ value: model.id, label: model.label }))
const ratioOptions = computed(() => selectedModel.value.aspectRatios.map((value) => ({ value, label: value })))
const resolutionOptions = computed(() => selectedModel.value.resolutions.map((value) => ({ value, label: value })))

function updateItem(id, patch) {
  updateNodeData(props.nodeId, {
    items: props.data.items.map((item) => item.id === id ? { ...item, ...patch } : item),
  })
}

function updateModel(modelId) {
  const model = getImageModel(modelId)
  updateNodeData(props.nodeId, {
    model: model.id,
    aspectRatio: model.aspectRatios.includes(props.data.aspectRatio) ? props.data.aspectRatio : model.defaultAspectRatio,
    resolution: model.resolutions.includes(props.data.resolution) ? props.data.resolution : model.defaultResolution,
  })
}

function changeCount(item, step) {
  updateItem(item.id, { count: Math.min(6, Math.max(1, item.count + step)), enabled: true })
}
</script>

<template>
  <section class="generation-panel product-visual-panel nodrag nowheel" @pointerdown.stop>
    <header class="product-visual-panel-header">
      <span><Images :size="16" />商品出图</span>
      <small v-if="productNode"><Package :size="13" />{{ productNode.data.product?.name || productNode.data.title }}</small>
    </header>

    <div class="product-visual-settings">
      <label><span>图片模型</span><AppSelect :model-value="selectedModel.id" :options="modelOptions" aria-label="图片模型" @update:model-value="updateModel" /></label>
      <label><span>画面比例</span><AppSelect :model-value="data.aspectRatio" :options="ratioOptions" aria-label="画面比例" @update:model-value="updateNodeData(nodeId, { aspectRatio: $event })" /></label>
      <label><span>清晰度</span><AppSelect :model-value="data.resolution" :options="resolutionOptions" aria-label="清晰度" @update:model-value="updateNodeData(nodeId, { resolution: $event })" /></label>
    </div>

    <div class="product-visual-groups">
      <section v-for="group in productVisualGroups" :key="group.id" class="product-visual-group">
        <h3><component :is="groupIcons[group.id]" :size="14" />{{ group.label }}</h3>
        <div class="product-visual-options">
          <div v-for="item in group.items" :key="item.id" class="product-visual-option" :class="{ active: data.items.find((value) => value.id === item.id)?.enabled }">
            <label>
              <input
                type="checkbox"
                :checked="data.items.find((value) => value.id === item.id)?.enabled"
                @change="updateItem(item.id, { enabled: $event.target.checked })"
              />
              <span>{{ item.label }}</span>
            </label>
            <div class="product-visual-stepper">
              <AppButton icon-only :disabled="!data.items.find((value) => value.id === item.id)?.enabled || data.items.find((value) => value.id === item.id)?.count <= 1" :aria-label="`减少${item.label}张数`" @click="changeCount(data.items.find((value) => value.id === item.id), -1)"><Minus :size="12" /></AppButton>
              <b>{{ data.items.find((value) => value.id === item.id)?.count || 1 }}</b>
              <AppButton icon-only :disabled="!data.items.find((value) => value.id === item.id)?.enabled || data.items.find((value) => value.id === item.id)?.count >= 6" :aria-label="`增加${item.label}张数`" @click="changeCount(data.items.find((value) => value.id === item.id), 1)"><Plus :size="12" /></AppButton>
            </div>
          </div>
        </div>
      </section>
    </div>

    <footer class="product-visual-panel-footer">
      <span>已选 {{ selectedItems.length }} 类</span>
      <strong>共 {{ totalCount }} 张</strong>
    </footer>
  </section>
</template>
