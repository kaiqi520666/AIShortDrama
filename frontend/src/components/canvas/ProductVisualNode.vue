<script setup>
import { useI18n } from 'vue-i18n'
import { canvasTemplateText } from '../../i18n/canvas'
import { computed } from 'vue'
import { Images, Package } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import StructuredNodeShell from './StructuredNodeShell.vue'

const { t } = useI18n()

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const store = useCanvasStore()
const productNode = computed(() => store.incomingNodes(props.id).find((node) => node.type === 'product'))
const selectedItems = computed(() => (props.data.items || []).filter((item) => item.enabled))
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Images" :selected="selected" has-target>
    <div class="product-visual-node-content nowheel">
      <div class="structured-node-summary">
        <span><Images :size="15" />{{ t('canvas.productVisual') }}</span>
        <small>{{ t('canvas.imageCount', { p0: selectedItems.length }) }}</small>
      </div>
      <div class="product-visual-source" :class="{ empty: !productNode }">
        <Package :size="15" />
        <span>{{ productNode?.data.product?.name || productNode?.data.title || t('canvas.productProfileDisconnected') }}</span>
      </div>
      <div class="product-visual-tags">
        <span v-for="item in selectedItems.slice(0, 6)" :key="item.id">{{ canvasTemplateText(item.id, item.label) }}</span>
        <span v-if="selectedItems.length > 6">+{{ selectedItems.length - 6 }}</span>
        <small v-if="!selectedItems.length">{{ t('canvas.noImageTypes') }}</small>
      </div>
    </div>
  </StructuredNodeShell>
</template>
