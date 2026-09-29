<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { CheckCircle2, Image, Shirt, UserRound } from 'lucide-vue-next'
import { useCanvasStore } from '../../stores/canvas'
import { resolveOutfitReference } from '../../config/canvas/outfit'
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
const targetHandles = [{ id: 'apparel', top: '48%' }]
const apparelNode = computed(() => store.incomingNodeByHandle(props.id, 'apparel'))
const apparelReference = computed(() => apparelNode.value && store.incomingNodes(apparelNode.value.id).find((node) => node.type === 'image'))
const reference = computed(() => resolveOutfitReference(props.data, store.nodes))
const inputs = computed(() => [
  { id: 'apparel', label: t('canvas.apparelRecognition'), icon: Shirt, asset: apparelReference.value?.data.asset, description: apparelNode.value ? t('canvas.enabledItems', { p0: (apparelNode.value.data.items || []).filter((item) => item.enabled !== false).length }) : t('canvas.waitingProfileConnection') },
  { id: 'model', label: t('canvas.model'), icon: UserRound, asset: props.data.modelReference?.url, description: props.data.modelReference?.name || (props.data.modelDescription ? t('canvas.textOrDefaultModel') : t('canvas.optional')) },
  { id: 'scene', label: t('canvas.scene'), icon: Image, asset: props.data.sceneReference?.url, description: props.data.sceneReference?.name || (props.data.sceneDescription ? t('canvas.textOrDefaultScene') : t('canvas.optional')) },
])
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Shirt" :selected="selected" :target-handles="targetHandles" :has-source="false">
    <div class="outfit-node-content nowheel">
      <div class="structured-node-summary">
        <span><Shirt :size="15" />{{ t('canvas.outfit') }}</span>
        <small>{{ reference.asset ? t('canvas.outfitReady') : t('canvas.waitingGeneration') }}</small>
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
        <img v-if="reference.asset" :src="buildOssImageUrl(reference.asset, { width: 480, quality: 84 })" :alt="t('canvas.outfitBoard')" referrerpolicy="no-referrer" />
        <template v-else><Shirt :size="24" /><strong>{{ t('canvas.outfitBoard') }}</strong><small>{{ t('canvas.confirmCreatesVideo') }}</small></template>
        <span v-if="reference.asset">{{ reference.legacy ? t('canvas.legacyOutfitBoard') : t('canvas.outfitBoard') }}</span>
      </div>
    </div>
  </StructuredNodeShell>
</template>
