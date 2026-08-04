<script setup>
import { computed } from 'vue'
import { Clapperboard, Package } from 'lucide-vue-next'
import { storyboardSegmentCount, storyboardShotCount } from '../../config/canvas/productStoryboard'
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
const selectedTemplates = computed(() => (props.data.templates || []).filter((item) => item.enabled))
const segmentCount = computed(() => storyboardSegmentCount(props.data.duration))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Clapperboard" :selected="selected" has-target>
    <div class="product-visual-node-content storyboard-node-content nowheel">
      <div class="structured-node-summary">
        <span><Clapperboard :size="15" />商品分镜</span>
        <small>{{ selectedTemplates.length }} 个分镜板</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !productNode }">
        <Package :size="15" />
        <span>{{ productNode?.data.product?.name || productNode?.data.title || '未连接商品创作' }}</span>
      </div>
      <div class="product-visual-tags storyboard-node-tags">
        <span v-for="item in selectedTemplates" :key="item.id">{{ item.label }}</span>
        <small v-if="!selectedTemplates.length">尚未选择脚本模板</small>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary">
        <span>{{ data.duration }} 秒 · {{ segmentCount }} 段</span><span>每段 {{ storyboardShotCount(15) }} 格</span><span>{{ data.characterReferences?.length || 0 }} 个角色 · {{ data.productReferences?.length || 0 }} 张商品图</span><span>{{ data.videoAspectRatio }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
