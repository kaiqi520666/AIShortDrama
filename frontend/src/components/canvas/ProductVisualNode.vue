<script setup>
import { computed } from 'vue'
import { Images, Package } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const productNode = computed(() => store.incomingNodes(props.id).find((node) => node.type === 'product'))
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
const totalCount = computed(() => selectedItems.value.reduce((sum, item) => sum + item.count, 0))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Images" :selected="selected" has-target>
    <div class="product-visual-node-content nodrag nopan nowheel">
      <div class="structured-node-summary">
        <span><Images :size="15" />商品出图</span>
        <small>{{ selectedItems.length }} 类 · {{ totalCount }} 张</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !productNode }">
        <Package :size="15" />
        <span>{{ productNode?.data.product?.name || productNode?.data.title || '未连接商品资料' }}</span>
      </div>
      <div class="product-visual-tags">
        <span v-for="item in selectedItems.slice(0, 6)" :key="item.id">{{ item.label }}<b v-if="item.count > 1">×{{ item.count }}</b></span>
        <span v-if="selectedItems.length > 6">+{{ selectedItems.length - 6 }}</span>
        <small v-if="!selectedItems.length">尚未选择图种</small>
      </div>
    </div>
  </StructuredNodeShell>
</template>
