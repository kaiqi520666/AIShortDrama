<script setup>
import { computed } from 'vue'
import { CheckCircle2, Image, Shirt } from 'lucide-vue-next'
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
const reference = computed(() => store.incomingNodes(props.id).find((node) => node.type === 'image'))
const enabledItems = computed(() => (props.data.items || []).filter((item) => item.enabled !== false))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" has-target>
    <div class="apparel-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />服饰资料</span>
        <small>{{ data.compositionType === 'set' ? '整套' : '单品' }} · {{ enabledItems.length }} 件</small>
      </div>
      <div class="outfit-source" :class="{ empty: !reference?.data.asset }">
        <span class="outfit-source-preview">
          <img v-if="reference?.data.asset" :src="buildOssImageUrl(reference.data.asset, { width: 160, quality: 80 })" alt="服饰参考图" referrerpolicy="no-referrer" />
          <Image v-else :size="18" />
        </span>
        <span><strong>服饰参考图</strong><small>{{ reference?.data.asset ? reference.data.title : '等待上传图片' }}</small></span>
        <CheckCircle2 v-if="reference?.data.asset" :size="16" />
      </div>
      <div class="product-visual-tags apparel-node-items">
        <span v-for="item in enabledItems.slice(0, 5)" :key="item.id">{{ item.name || item.category || '未命名单品' }}</span>
        <span v-if="enabledItems.length > 5">+{{ enabledItems.length - 5 }}</span>
        <small v-if="!enabledItems.length">等待 AI 识别或手动添加</small>
      </div>
    </div>
  </StructuredNodeShell>
</template>
