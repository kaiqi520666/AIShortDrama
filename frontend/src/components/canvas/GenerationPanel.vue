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
  const imageInputs = promptParts.value.filter((part) => part.type === 'image').reduce((items, part) => {
    if (items.some((item) => item.node.id === part.nodeId)) return items
    const node = imageReferences.value.find((item) => item.id === part.nodeId)
    if (node) items.push({ key: node.id, node, number: items.length + 1 })
    return items
  }, [])
  return [...textInputs, ...imageInputs]
})

function updatePrompt(parts) {
  const imageIds = []
  updateNodeData(props.nodeId, {
    promptParts: parts,
    prompt: parts.map((part) => {
      if (part.type !== 'image') return part.value
      let index = imageIds.indexOf(part.nodeId)
      if (index < 0) {
        imageIds.push(part.nodeId)
        index = imageIds.length - 1
      }
      return `图片${index + 1}`
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
