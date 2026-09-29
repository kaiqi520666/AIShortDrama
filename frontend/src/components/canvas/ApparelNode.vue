<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { CheckCircle2, Image, Shirt } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import StructuredNodeShell from './StructuredNodeShell.vue'

const { t } = useI18n()

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
        <span><Shirt :size="15" />{{ t('canvas.apparelRecognition') }}</span>
        <small>{{ t('canvas.apparelCount', { p0: data.compositionType === 'set' ? t('canvas.fullSet') : t('canvas.singleItem'), p1: enabledItems.length }) }}</small>
      </div>
      <div class="outfit-source" :class="{ empty: !reference?.data.asset }">
        <span class="outfit-source-preview">
          <img v-if="reference?.data.asset" :src="buildOssImageUrl(reference.data.asset, { width: 160, quality: 80 })" :alt="t('canvas.apparelReference')" referrerpolicy="no-referrer" />
          <Image v-else :size="18" />
        </span>
        <span><strong>{{ t('canvas.apparelReference') }}</strong><small>{{ reference?.data.asset ? reference.data.title : t('canvas.waitingUpload') }}</small></span>
        <CheckCircle2 v-if="reference?.data.asset" :size="16" />
      </div>
      <div class="product-visual-tags apparel-node-items">
        <span v-for="item in enabledItems.slice(0, 5)" :key="item.id">{{ item.name || item.category || t('canvas.unnamedItem') }}</span>
        <span v-if="enabledItems.length > 5">+{{ enabledItems.length - 5 }}</span>
        <small v-if="!enabledItems.length">{{ t('canvas.waitingRecognitionOrAdd') }}</small>
      </div>
    </div>
  </StructuredNodeShell>
</template>
