<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, ChevronDown, FileText, Image, Video as VideoIcon, WandSparkles } from 'lucide-vue-next'
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
const imageResolutions = ['1K', '2K', '4K']
const videoAspectRatios = ['21:9', '16:9', '4:3', '1:1', '3:4', '9:16', 'adaptive']
const videoModels = [
  { value: 'seedance-2', label: 'Seedance 2', resolutions: ['480p', '720p', '1080p', '4k'] },
  { value: 'seedance-2-fast', label: 'Seedance 2 Fast', resolutions: ['480p', '720p'] },
  { value: 'seedance-2-mini', label: 'Seedance 2 Mini', resolutions: ['480p', '720p'], durations: [4, 8, 10, 12, 15] },
]
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const selectedResolution = computed(() => props.data.resolution || (props.type === 'video' ? '720p' : '2K'))
const selectedAspectRatio = computed(() => props.data.aspectRatio || '16:9')
const selectedDuration = computed(() => props.data.duration ?? 5)
const selectedVideoModel = computed(() => videoModels.find((model) => model.value === props.data.model) || videoModels[0])
const settingLabel = computed(() => {
  if (props.type === 'image') return `${selectedAspectRatio.value} · ${selectedResolution.value}`
  if (props.type === 'video') return `${selectedAspectRatio.value === 'adaptive' ? '自适应' : selectedAspectRatio.value} · ${selectedResolution.value} · ${selectedDuration.value === 0 ? '自动' : `${selectedDuration.value}s`}`
  return mediaTypes[props.type].setting
})
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
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function updateVideoModel(model) {
  const updates = { model: model.value }
  if (!model.resolutions.includes(selectedResolution.value)) updates.resolution = '720p'
  if (model.durations && !model.durations.includes(selectedDuration.value)) updates.duration = 10
  updateNodeData(props.nodeId, updates)
}

function updateVideoSetting(key, value) {
  updateNodeData(props.nodeId, { [key]: value })
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function updateSettingsPosition() {
  if (!settingsTrigger.value || !settingsMenu.value) return
  const panelRect = settingsTrigger.value.closest('.generation-panel').getBoundingClientRect()
  const triggerRect = settingsTrigger.value.getBoundingClientRect()
  const menuHeight = settingsMenu.value.offsetHeight
  const menuWidth = settingsMenu.value.offsetWidth
  const gap = 8
  const centeredLeft = triggerRect.left - panelRect.left + (triggerRect.width - menuWidth) / 2
  const left = Math.min(Math.max(0, centeredLeft), Math.max(0, panelRect.width - menuWidth))
  const top = triggerRect.top - menuHeight - gap >= 12
    ? triggerRect.top - panelRect.top - menuHeight - gap
    : triggerRect.bottom - panelRect.top + gap
  settingsStyle.value = { left: `${left}px`, top: `${top}px` }
}

function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) nextTick(updateSettingsPosition)
}

function closeSettings(event) {
  if (settingsOpen.value && !event.target.closest('.media-settings-menu, .media-settings-trigger')) settingsOpen.value = false
}

onMounted(() => window.addEventListener('pointerdown', closeSettings))
onBeforeUnmount(() => window.removeEventListener('pointerdown', closeSettings))
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

    <div v-if="settingsOpen && ['image', 'video'].includes(type)" ref="settingsMenu" class="image-settings-menu media-settings-menu" :style="settingsStyle" @pointerdown.stop>
      <template v-if="type === 'image'">
        <h3>清晰度</h3>
        <div class="image-resolution-options">
          <button v-for="resolution in imageResolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateImageSetting('resolution', resolution)">
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
      </template>

      <template v-else>
        <h3>模型</h3>
        <div class="video-model-options">
          <button v-for="model in videoModels" :key="model.value" :class="{ active: selectedVideoModel.value === model.value }" @click="updateVideoModel(model)">{{ model.label.replace('Seedance 2 ', '') }}</button>
        </div>

        <h3>时长</h3>
        <div v-if="selectedVideoModel.durations" class="video-duration-options">
          <button v-for="duration in selectedVideoModel.durations" :key="duration" :class="{ active: selectedDuration === duration }" @click="updateVideoSetting('duration', duration)">{{ duration }}s</button>
        </div>
        <div v-else class="video-duration-slider">
          <button :class="{ active: selectedDuration === 0 }" @click="updateVideoSetting('duration', 0)">自动</button>
          <input type="range" min="4" max="15" step="1" :value="selectedDuration || 5" aria-label="视频时长" @input="updateVideoSetting('duration', Number($event.target.value))" />
          <span>{{ selectedDuration === 0 ? '自动' : `${selectedDuration}s` }}</span>
        </div>

        <h3>清晰度</h3>
        <div class="image-resolution-options">
          <button v-for="resolution in selectedVideoModel.resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateVideoSetting('resolution', resolution)">{{ resolution === '4k' ? '4K' : resolution }}</button>
        </div>

        <h3>比例</h3>
        <div class="image-ratio-grid video-ratio-grid">
          <button v-for="ratio in videoAspectRatios" :key="ratio" :class="{ active: selectedAspectRatio === ratio }" @click="updateVideoSetting('aspectRatio', ratio)">
            <span v-if="ratio !== 'adaptive'" class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
            <span v-else class="adaptive-ratio-icon">A</span>
            <strong>{{ ratio === 'adaptive' ? '自适应' : ratio }}</strong>
          </button>
        </div>

        <h3>输出</h3>
        <label class="video-toggle-row">
          <span>生成同步音频</span>
          <input type="checkbox" :checked="data.generateAudio ?? true" @change="updateVideoSetting('generateAudio', $event.target.checked)" />
        </label>
      </template>
    </div>

    <p v-if="notice" class="panel-notice">{{ notice }}</p>

    <footer>
      <span class="model-select"><WandSparkles :size="16" />{{ type === 'video' ? selectedVideoModel.label : data.model }}</span>
      <span v-if="type !== 'text'" class="panel-divider"></span>
      <button v-if="['image', 'video'].includes(type)" ref="settingsTrigger" class="image-settings-trigger media-settings-trigger" @click="toggleSettings">
        <component :is="type === 'video' ? VideoIcon : Image" :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </button>
      <span v-else-if="type !== 'text'" class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
      <button class="run-task-button" :disabled="!canSubmit" title="执行" @click="submitTask"><ArrowUp :size="20" /></button>
    </footer>
  </section>
</template>
