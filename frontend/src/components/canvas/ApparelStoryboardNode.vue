<script setup>
import { computed } from 'vue'
import { Clapperboard, Images, Shirt, UserRound } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import { getApparelVideoSettings } from '../../config/canvas/outfitStoryboard'
import { buildOssImageUrl } from '../../utils/ossImage'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const targetHandles = [
  { id: 'apparel', top: '38%', label: '服饰' },
  { id: 'model', top: '61%', label: '角色' },
  { id: 'scene', top: '84%', label: '场景' },
]

function inputNode(handle) {
  const edge = store.edges.find((item) => item.target === props.id && item.targetHandle === handle)
  return store.nodes.find((node) => node.id === edge?.source)
}

const apparelNode = computed(() => inputNode('apparel'))
const garmentNode = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image'))
const modelNode = computed(() => inputNode('model'))
const sceneNode = computed(() => inputNode('scene'))
const generatedCount = computed(() => (props.data.generatedNodeIds || []).filter((id) => store.nodes.some((node) => node.id === id)).length)
const settings = computed(() => getApparelVideoSettings(props.data))
const inputs = computed(() => [
  { label: '服饰资料', icon: Shirt, node: apparelNode.value, asset: garmentNode.value?.data.asset, detail: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '等待连接' },
  { label: '角色节点', icon: UserRound, node: modelNode.value, asset: modelNode.value?.data.asset, detail: modelNode.value?.data.title || '等待连接' },
  { label: '场景节点', icon: Images, node: sceneNode.value, asset: sceneNode.value?.data.asset, detail: sceneNode.value?.data.title || '等待连接' },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Clapperboard" :selected="selected" :target-handles="targetHandles">
    <div class="product-visual-node-content storyboard-node-content apparel-storyboard-node-content nowheel">
      <div class="structured-node-summary">
        <span><Clapperboard :size="15" />服饰分镜</span>
        <small>{{ generatedCount ? '故事板 + 视频已创建' : '等待生成方案' }}</small>
      </div>
      <div class="apparel-storyboard-inputs">
        <div v-for="item in inputs" :key="item.label" class="product-visual-source" :class="{ empty: !item.asset }">
          <span class="outfit-source-preview">
            <img v-if="item.asset" :src="buildOssImageUrl(item.asset, { width: 120, quality: 78 })" :alt="item.label" referrerpolicy="no-referrer" />
            <component :is="item.icon" v-else :size="16" />
          </span>
          <span><strong>{{ item.label }}</strong><small>{{ item.detail }}</small></span>
        </div>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary apparel-storyboard-node-summary">
        <span>{{ settings.duration }} 秒</span><span>{{ data.storyboardShotCount || '按时长' }} 格</span><span>{{ settings.aspectRatio }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
