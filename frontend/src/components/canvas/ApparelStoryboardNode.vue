<script setup>
import { computed } from 'vue'
import { Clapperboard, Images, Shirt } from 'lucide-vue-next'
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
const targetHandles = [{ id: 'outfit', top: '48%' }, { id: 'scene', top: '78%' }]
const outfitNode = computed(() => store.incomingNodeByHandle(props.id, 'outfit'))
const sceneNode = computed(() => store.incomingNodeByHandle(props.id, 'scene'))
const generatedCount = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)).length)
const inputs = computed(() => [
  { label: '模特试穿', icon: Shirt, asset: outfitNode.value?.data.outfitBoardAsset },
  { label: '场景', icon: Images, asset: sceneNode.value?.data.asset },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Clapperboard" :selected="selected" :target-handles="targetHandles">
    <div class="product-visual-node-content storyboard-node-content apparel-storyboard-node-content nowheel">
      <div class="structured-node-summary">
        <span><Clapperboard :size="15" />服饰分镜</span>
        <small>{{ generatedCount ? '已生成' : '待生成' }}</small>
      </div>
      <div class="apparel-storyboard-inputs">
        <div v-for="item in inputs" :key="item.label" class="product-visual-source" :class="{ empty: !item.asset }">
          <span class="outfit-source-preview">
            <img v-if="item.asset" :src="buildOssImageUrl(item.asset, { width: 120, quality: 78 })" :alt="item.label" referrerpolicy="no-referrer" />
            <component :is="item.icon" v-else :size="16" />
          </span>
          <span><strong>{{ item.label }}</strong></span>
        </div>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary apparel-storyboard-node-summary">
        <span>{{ data.duration }} 秒</span><span>{{ Number(data.duration || 15) / 15 }} 段</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
