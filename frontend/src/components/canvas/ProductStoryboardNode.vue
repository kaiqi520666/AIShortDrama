<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { Clapperboard, Package } from 'lucide-vue-next'
import { getStoryboardDurations, storyboardSegmentCount, storyboardShotCount } from '../../config/canvas/productStoryboard'
import { useCanvasStore } from '../../stores/canvas'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import StructuredNodeShell from './StructuredNodeShell.vue'

const { t } = useI18n()

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
        <span><Clapperboard :size="15" />{{ t('canvas.productStoryboard') }}</span>
        <small>{{ t('canvas.ugc') }}</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !productNode }">
        <Package :size="15" />
        <span>{{ productNode?.data.product?.name || productNode?.data.title || t('canvas.productCreationDisconnected') }}</span>
      </div>
      <div class="product-visual-tags storyboard-node-tags">
        <span>{{ t('canvas.ugc') }}</span>
      </div>
      <div class="product-creation-settings-summary storyboard-node-summary">
        <span>{{ t('canvas.durationSegments', { p0: data.duration, p1: segmentCount }) }}</span><span>{{ t('canvas.shotsPerSegment', { p0: storyboardShotCount(15) }) }}</span><span>{{ t('canvas.referenceCounts', { p0: data.characterReferences?.length || 0, p1: data.productReferences?.length || 0 }) }}</span><span>{{ data.videoAspectRatio }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
