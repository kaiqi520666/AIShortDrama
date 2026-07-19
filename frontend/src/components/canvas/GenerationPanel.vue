<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, ChevronDown, FileText, Image, WandSparkles } from 'lucide-vue-next'
import { imageAspectRatios } from '../../config/imageSettings'
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
const settingsTrigger = ref(null)
const settingsMenu = ref(null)
const settingsOpen = ref(false)
const settingsStyle = ref({})
const notice = ref('')
const resolutions = ['1K', '2K', '4K']
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const selectedResolution = computed(() => props.data.resolution || '2K')
const selectedAspectRatio = computed(() => props.data.aspectRatio || '16:9')
const settingLabel = computed(() => props.type === 'image' ? `${selectedAspectRatio.value} · ${selectedResolution.value}` : mediaTypes[props.type].setting)
const displayReferences = computed(() => {
  const counts = { text: 0, image: 0, video: 0, audio: 0 }
  const inputs = props.type === 'text' ? references.value.filter((node) => ['text', 'image'].includes(node.type)) : references.value
  return inputs.map((node) => ({ key: node.id, node, number: ++counts[node.type], label: `${mediaTypes[node.type].label}${counts[node.type]}` }))
})
const canSubmit = computed(() => {
  if (!props.data.prompt?.trim()) return false
  if (props.type !== 'text') return true
  return references.value.some((node) => node.type === 'image' ? node.data.asset : node.type === 'text' && node.data.content?.trim())
})

function updatePrompt(parts) {
  notice.value = ''
  updateNodeData(props.nodeId, {
    promptParts: parts,
    prompt: parts.map((part) => {
      if (part.type !== 'image') return part.value
      return `图片${imageReferences.value.findIndex((node) => node.id === part.nodeId) + 1}`
    }).join(''),
  })
}

function updateTextPrompt(event) {
  notice.value = ''
  updateNodeData(props.nodeId, { prompt: event.target.value })
}

function submitTask() {
  notice.value = '模型暂未接入'
}

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(16 / width, 16 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}

function updateImageSetting(key, value) {
  const resolution = key === 'resolution' ? value : selectedResolution.value
  const aspectRatio = key === 'aspectRatio' ? value : selectedAspectRatio.value
  const ratio = imageAspectRatios.find((item) => item.value === aspectRatio)
  updateNodeData(props.nodeId, { [key]: value, dimensions: ratio.sizes[resolution] })
}

function updateSettingsPosition() {
  if (!settingsTrigger.value || !settingsMenu.value) return
  const triggerRect = settingsTrigger.value.getBoundingClientRect()
  const menuHeight = settingsMenu.value.offsetHeight
  const menuWidth = settingsMenu.value.offsetWidth
  const gap = 8
  const centeredLeft = triggerRect.left + (triggerRect.width - menuWidth) / 2
  const left = Math.min(Math.max(12, centeredLeft), window.innerWidth - menuWidth - 12)
  const top = triggerRect.top - menuHeight - gap >= 12 ? triggerRect.top - menuHeight - gap : triggerRect.bottom + gap
  settingsStyle.value = { left: `${left}px`, top: `${top}px` }
}

function toggleImageSettings() {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) nextTick(updateSettingsPosition)
}

function closeImageSettings(event) {
  if (settingsOpen.value && !event.target.closest('.image-settings-menu, .image-settings-trigger')) settingsOpen.value = false
}

onMounted(() => window.addEventListener('pointerdown', closeImageSettings))
onBeforeUnmount(() => window.removeEventListener('pointerdown', closeImageSettings))
</script>

<template>
  <section v-if="type !== 'text' || data.textMode === 'task'" class="generation-panel nodrag nowheel" @pointerdown.stop>
    <div v-if="displayReferences.length" class="reference-strip">
      <div v-for="reference in displayReferences" :key="reference.key" class="reference-item" :title="reference.label" :aria-label="reference.label">
        <img v-if="reference.node.data.asset" :src="reference.node.data.asset" alt="" />
        <FileText v-else-if="reference.node.type === 'text'" :size="20" />
        <Image v-else-if="reference.node.type === 'image'" :size="20" />
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
      @pointerdown="settingsOpen = false"
    />
    <textarea
      v-else
      :value="data.prompt"
      :placeholder="mediaTypes[type].placeholder"
      @input="updateTextPrompt"
      @pointerdown="settingsOpen = false"
    ></textarea>

    <div v-if="settingsOpen && type === 'image'" ref="settingsMenu" class="image-settings-menu" :style="settingsStyle" @pointerdown.stop>
      <h3>清晰度</h3>
      <div class="image-resolution-options">
        <button v-for="resolution in resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateImageSetting('resolution', resolution)">
          {{ resolution }}
        </button>
      </div>
      <h3>比例</h3>
      <div class="image-ratio-grid">
        <button v-for="ratio in imageAspectRatios" :key="ratio.value" :class="{ active: selectedAspectRatio === ratio.value }" @click="updateImageSetting('aspectRatio', ratio.value)">
          <span class="image-ratio-icon" :style="ratioIconStyle(ratio.value)"></span>
          <strong>{{ ratio.value }}</strong>
        </button>
      </div>
    </div>

    <p v-if="notice" class="panel-notice">{{ notice }}</p>

    <footer>
      <span class="model-select"><WandSparkles :size="16" />{{ data.model }}</span>
      <span v-if="type !== 'text'" class="panel-divider"></span>
      <button v-if="type === 'image'" ref="settingsTrigger" class="image-settings-trigger" @click="toggleImageSettings">
        <Image :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </button>
      <span v-else-if="type !== 'text'" class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
      <button class="run-task-button" :disabled="!canSubmit" title="执行" @click="submitTask"><ArrowUp :size="20" /></button>
    </footer>
  </section>
</template>
