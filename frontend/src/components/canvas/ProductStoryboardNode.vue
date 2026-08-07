<script setup>
import { computed } from 'vue'
import { Clapperboard, Package } from 'lucide-vue-next'
import { getStoryboardDurations, storyboardSegmentCount, storyboardShotCount } from '../../config/canvas/productStoryboard'
import { useCanvasStore } from '../../stores/canvas'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const contentTemplateStore = useContentTemplatesStore()
const productNode = computed(() => store.incomingNodes(props.id).find((node) => node.type === 'product'))
const segmentCount = computed(() => storyboardSegmentCount(
  props.data.duration,
  getStoryboardDurations(contentTemplateStore.templates.product_storyboard),
))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Clapperboard" :selected="selected" has-target>
    <div class="product-visual-node-content storyboard-node-content nowheel">
      <div class="structured-node-summary">
        <span><Clapperboard :size="15" />商品分镜</span>
        <small>UGC 种草</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !productNode }">
        <Package :size="15" />
        <span>{{ productNode?.data.product?.name || productNode?.data.title || '未连接商品创作' }}</span>
      </div>
      <div class="product-visual-tags storyboard-node-tags">
        <span>UGC 种草</span>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary">
        <span>{{ data.duration }} 秒 · {{ segmentCount }} 段</span><span>每段 {{ storyboardShotCount(15) }} 格</span><span>{{ data.characterReferences?.length || 0 }} 个角色 · {{ data.productReferences?.length || 0 }} 张商品图</span><span>{{ data.videoAspectRatio }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
