<script setup>
import { computed } from 'vue'
import { CheckCircle2, Shirt, UserRound } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
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
const inputs = computed(() => [
  { id: 'apparel', label: '服饰资料', icon: Shirt, node: apparelNode.value, asset: apparelReference.value?.data.asset, description: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '等待连接资料' },
  { id: 'model', label: '模特参考图', icon: UserRound, node: inputNode('model'), asset: inputNode('model')?.data.asset, description: inputNode('model')?.data.title || '等待选择图片' },
])
const materialCount = computed(() => props.data.moduleIds?.length || 0)
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" :target-handles="targetHandles">
    <div class="outfit-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />穿搭素材</span>
        <small>{{ materialCount }} 项 · {{ inputs.filter((item) => item.asset).length }}/2 就绪</small>
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
    </div>
  </StructuredNodeShell>
</template>
