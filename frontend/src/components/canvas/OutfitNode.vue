<script setup>
import { computed } from 'vue'
import { CheckCircle2, Shirt, UserRound } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import { outfitMaterials } from '../../config/canvas/outfit'
import { buildOssImageUrl } from '../../utils/ossImage'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const targetHandles = [{ id: 'apparel', top: '48%' }, { id: 'model', top: '78%' }]

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.id && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const apparelNode = computed(() => inputNode('apparel'))
const apparelReference = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image'))
const generatedNodes = computed(() => (props.data.generatedNodeIds || []).map((id) => store.nodes.find((node) => node.id === id)).filter(Boolean))
const boardItems = computed(() => outfitMaterials.map((item) => ({
  ...item,
  node: generatedNodes.value.find((node) => node.data.outfitMaterialId === item.id),
})))
const readyCount = computed(() => boardItems.value.filter((item) => item.node?.data.asset).length)
const inputs = computed(() => [
  { id: 'apparel', label: '服饰资料', icon: Shirt, node: apparelNode.value, asset: apparelReference.value?.data.asset, description: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '等待连接资料' },
  { id: 'model', label: '模特参考图', icon: UserRound, node: inputNode('model'), asset: inputNode('model')?.data.asset, description: inputNode('model')?.data.title || '等待选择图片' },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" :target-handles="targetHandles">
    <div class="outfit-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />穿搭素材</span>
        <small>6 格 · {{ readyCount }}/6 就绪</small>
      </div>
      <div class="outfit-sources">
        <div v-for="item in inputs" :key="item.id" class="outfit-source" :class="{ empty: !item.asset }">
          <span class="outfit-source-preview">
            <img v-if="item.asset" :src="buildOssImageUrl(item.asset, { width: 160, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
            <component :is="item.icon" v-else :size="18" />
          </span>
          <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
          <CheckCircle2 v-if="item.asset" :size="16" />
        </div>
      </div>
      <div class="outfit-board-preview">
        <div v-for="(item, index) in boardItems" :key="item.id" class="outfit-board-cell" :class="{ ready: item.node?.data.asset }">
          <img v-if="item.node?.data.asset" :src="buildOssImageUrl(item.node.data.asset, { width: 180, quality: 78 })" :alt="item.label" referrerpolicy="no-referrer" />
          <span v-else>{{ index + 1 }}</span>
          <small>{{ item.label }}</small>
        </div>
      </div>
    </div>
  </StructuredNodeShell>
</template>
