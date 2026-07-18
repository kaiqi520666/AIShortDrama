<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { Check, ChevronDown, FileText, Image, WandSparkles } from 'lucide-vue-next'
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
const settingsOpen = ref(false)
const resolutions = ['1K', '2K', '4K']
const aspectRatios = [
  { value: '1:1', sizes: { '1K': '1024x1024', '2K': '2048x2048', '4K': '2880x2880' } },
  { value: '3:2', sizes: { '1K': '1536x1024', '2K': '2048x1360', '4K': '3520x2336' } },
  { value: '2:3', sizes: { '1K': '1024x1536', '2K': '1360x2048', '4K': '2336x3520' } },
  { value: '4:3', sizes: { '1K': '1024x768', '2K': '2048x1536', '4K': '3312x2480' } },
  { value: '3:4', sizes: { '1K': '768x1024', '2K': '1536x2048', '4K': '2480x3312' } },
  { value: '5:4', sizes: { '1K': '1280x1024', '2K': '2560x2048', '4K': '3216x2576' } },
  { value: '4:5', sizes: { '1K': '1024x1280', '2K': '2048x2560', '4K': '2576x3216' } },
  { value: '16:9', sizes: { '1K': '1536x864', '2K': '2048x1152', '4K': '3840x2160' } },
  { value: '9:16', sizes: { '1K': '864x1536', '2K': '1152x2048', '4K': '2160x3840' } },
  { value: '2:1', sizes: { '1K': '2048x1024', '2K': '2688x1344', '4K': '3840x1920' } },
  { value: '1:2', sizes: { '1K': '1024x2048', '2K': '1344x2688', '4K': '1920x3840' } },
  { value: '21:9', sizes: { '1K': '2016x864', '2K': '2688x1152', '4K': '3840x1648' } },
  { value: '9:21', sizes: { '1K': '864x2016', '2K': '1152x2688', '4K': '1648x3840' } },
]
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const selectedResolution = computed(() => props.data.resolution || '2K')
const selectedAspectRatio = computed(() => props.data.aspectRatio || '16:9')
const settingLabel = computed(() => props.type === 'image' ? `${selectedAspectRatio.value} · ${selectedResolution.value} · 1张` : mediaTypes[props.type].setting)
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

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(24 / width, 24 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}

function updateImageSetting(key, value) {
  const resolution = key === 'resolution' ? value : selectedResolution.value
  const aspectRatio = key === 'aspectRatio' ? value : selectedAspectRatio.value
  const ratio = aspectRatios.find((item) => item.value === aspectRatio)
  updateNodeData(props.nodeId, { [key]: value, dimensions: ratio.sizes[resolution] })
}

function closeImageSettings(event) {
  if (settingsOpen.value && !event.target.closest('.image-settings-menu, .image-settings-trigger')) settingsOpen.value = false
}

onMounted(() => window.addEventListener('pointerdown', closeImageSettings))
onBeforeUnmount(() => window.removeEventListener('pointerdown', closeImageSettings))
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

    <div v-if="settingsOpen && type === 'image'" class="image-settings-menu" @pointerdown.stop>
      <h3>清晰度</h3>
      <div class="image-resolution-options">
        <button v-for="resolution in resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateImageSetting('resolution', resolution)">
          {{ resolution }}
          <Check v-if="selectedResolution === resolution" :size="16" />
        </button>
      </div>
      <h3>比例</h3>
      <div class="image-ratio-grid">
        <button v-for="ratio in aspectRatios" :key="ratio.value" :class="{ active: selectedAspectRatio === ratio.value }" @click="updateImageSetting('aspectRatio', ratio.value)">
          <span class="image-ratio-icon" :style="ratioIconStyle(ratio.value)"></span>
          <strong>{{ ratio.value }}</strong>
        </button>
      </div>
    </div>

    <footer>
      <span class="model-select"><WandSparkles :size="16" />{{ data.model }}</span>
      <span class="panel-divider"></span>
      <button v-if="type === 'image'" class="image-settings-trigger" @click="settingsOpen = !settingsOpen">
        <Image :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </button>
      <span v-else class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
    </footer>
  </section>
</template>
