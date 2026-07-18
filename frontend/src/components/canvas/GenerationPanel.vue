<script setup>
import { computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { Image, WandSparkles } from 'lucide-vue-next'
import { mediaTypes } from '../../config/mediaTypes'
import { useCanvasStore } from '../../stores/canvas'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  type: { type: String, required: true },
})

const store = useCanvasStore()
const { updateNodeData } = useVueFlow()
const references = computed(() => store.incomingNodes(props.nodeId))
</script>

<template>
  <section class="generation-panel nodrag nowheel" @pointerdown.stop>
    <div v-if="references.length" class="reference-strip">
      <div v-for="(reference, index) in references" :key="reference.id" class="reference-item">
        <img v-if="reference.data.asset" :src="reference.data.asset" alt="" />
        <span v-else>{{ index + 1 }}</span>
        <b>{{ index + 1 }}</b>
      </div>
    </div>

    <textarea
      :value="data.prompt"
      :placeholder="mediaTypes[type].placeholder"
      @input="updateNodeData(nodeId, { prompt: $event.target.value })"
    ></textarea>

    <footer>
      <span class="model-select"><WandSparkles :size="16" />{{ data.model }}</span>
      <span class="panel-divider"></span>
      <span class="setting-select"><Image :size="16" />{{ mediaTypes[type].setting }}</span>
    </footer>
  </section>
</template>
