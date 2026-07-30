<script setup>
import { computed } from 'vue'
import { Clapperboard, Images } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const outfitNode = computed(() => store.incomingNodes(props.id).find((node) => node.type === 'outfit'))
const generatedCount = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)).length)
const segmentCount = computed(() => Math.max(1, Number(props.data.duration || 15) / 15))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Clapperboard" :selected="selected" :target-handles="[{ id: 'outfit', top: '50%' }]">
    <div class="product-visual-node-content storyboard-node-content nowheel">
      <div class="structured-node-summary">
        <span><Clapperboard :size="15" />服饰分镜</span>
        <small>{{ segmentCount }} 段 · {{ generatedCount }} 个节点</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !outfitNode?.data.outfitBoardAsset }">
        <Images :size="15" />
        <span>{{ outfitNode?.data.outfitBoardAsset ? '2K · 9:16 服饰总览图' : '等待服饰总览图' }}</span>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary">
        <span>单模板</span><span>{{ data.duration }} 秒</span><span>每段 6 格</span><span>{{ data.videoAspectRatio }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
