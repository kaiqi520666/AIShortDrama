<script setup>
import { computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { FileText, Image, WandSparkles } from 'lucide-vue-next'
import { mediaTypes } from '../../config/mediaTypes'
import { useCanvasStore } from '../../stores/canvas'
import PromptReferenceEditor from './PromptReferenceEditor.vue'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, required: true },
  type: { type: String, required: true },
})

const store = useCanvasStore()
const { updateNodeData } = useVueFlow()
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const displayReferences = computed(() => {
  if (props.type !== 'image') return references.value.map((node, index) => ({ key: node.id, node, number: index + 1 }))
  const textInputs = references.value.filter((node) => node.type === 'text').map((node, index) => ({ key: `text-${node.id}`, node, number: index + 1 }))
  const imageInputs = imageReferences.value.map((node, index) => ({ key: node.id, node, number: index + 1 }))
  return [...textInputs, ...imageInputs]
})

function updatePrompt(parts) {
  updateNodeData(props.nodeId, {
    promptParts: parts,
    prompt: parts.map((part) => {
      if (part.type !== 'image') return part.value
      return `图片${imageReferences.value.findIndex((node) => node.id === part.nodeId) + 1}`
    }).join(''),
  })
}
</script>

<template>
  <section class="generation-panel nodrag nowheel" @pointerdown.stop>
    <div v-if="displayReferences.length" class="reference-strip">
      <div v-for="reference in displayReferences" :key="reference.key" class="reference-item">
        <img v-if="reference.node.data.asset" :src="reference.node.data.asset" alt="" />
        <FileText v-else-if="reference.node.type === 'text'" :size="20" />
        <span v-else>{{ reference.number }}</span>
        <b>{{ reference.number }}</b>
      </div>
    </div>

    <PromptReferenceEditor
      v-if="type === 'image'"
      :model-value="promptParts"
      :references="imageReferences"
      :placeholder="mediaTypes[type].placeholder"
      @update:model-value="updatePrompt"
    />
    <textarea
      v-else
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
