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
const targetHandles = [{ id: 'garment', top: '48%' }, { id: 'model', top: '78%' }]

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.id && item.targetHandle === handle)
  return store.nodes.find((item) => item.id === edge?.source)
}

const inputs = computed(() => [
  { id: 'garment', label: '服饰参考图', icon: Shirt, node: inputNode('garment') },
  { id: 'model', label: '模特参考图', icon: UserRound, node: inputNode('model') },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" :target-handles="targetHandles">
    <div class="outfit-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />服饰穿搭</span>
        <small>{{ inputs.filter((item) => item.node?.data.asset).length }}/2 已选择</small>
      </div>
      <div class="outfit-sources">
        <div v-for="item in inputs" :key="item.id" class="outfit-source" :class="{ empty: !item.node?.data.asset }">
          <span class="outfit-source-preview">
            <img v-if="item.node?.data.asset" :src="buildOssImageUrl(item.node.data.asset, { width: 160, quality: 80 })" :alt="item.label" referrerpolicy="no-referrer" />
            <component :is="item.icon" v-else :size="18" />
          </span>
          <span><strong>{{ item.label }}</strong><small>{{ item.node?.data.asset ? item.node.data.title : '等待选择图片' }}</small></span>
          <CheckCircle2 v-if="item.node?.data.asset" :size="16" />
        </div>
      </div>
    </div>
  </StructuredNodeShell>
</template>
