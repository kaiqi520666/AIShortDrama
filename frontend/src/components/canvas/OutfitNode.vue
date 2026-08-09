<script setup>
import { computed } from 'vue'
import { CheckCircle2, Shirt, UserRound } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import { resolveOutfitReference } from '../../config/canvas/outfit'
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
const apparelNode = computed(() => store.incomingNodeByHandle(props.id, 'apparel'))
const apparelReference = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image'))
const modelNode = computed(() => store.incomingNodeByHandle(props.id, 'model'))
const reference = computed(() => resolveOutfitReference(props.data, store.nodes))
const inputs = computed(() => [
  { id: 'apparel', label: '服饰识别', icon: Shirt, asset: apparelReference.value?.data.asset, description: apparelNode.value ? `${(apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length} 件已启用` : '等待连接资料' },
  { id: 'model', label: '模特参考图', icon: UserRound, asset: modelNode.value?.data.asset, description: modelNode.value?.data.title || '等待选择图片' },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" :target-handles="targetHandles">
    <div class="outfit-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />服饰穿搭</span>
        <small>{{ reference.asset ? '定妆图已就绪' : '等待生成' }}</small>
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
      <div class="outfit-reference-preview" :class="{ empty: !reference.asset }">
        <img v-if="reference.asset" :src="buildOssImageUrl(reference.asset, { width: 480, quality: 84 })" alt="试穿定妆图" referrerpolicy="no-referrer" />
        <template v-else><Shirt :size="24" /><strong>试穿定妆图</strong><small>生成后用于服饰分镜</small></template>
        <span v-if="reference.asset">{{ reference.legacy ? '旧版试穿总览' : '试穿定妆图' }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
