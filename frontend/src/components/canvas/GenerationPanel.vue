<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { ArrowUp, ChevronDown, FileText, Image, Video as VideoIcon, WandSparkles } from 'lucide-vue-next'
import { imageModels, normalizeImageSettings } from '../../config/imageModels'
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
const modelTrigger = ref(null)
const modelMenu = ref(null)
const modelOpen = ref(false)
const modelStyle = ref({})
const notice = ref('')
const videoAspectRatios = ['21:9', '16:9', '4:3', '1:1', '3:4', '9:16', 'adaptive']
const videoModels = [
  { value: 'seedance-2', label: 'Seedance 2', resolutions: ['480p', '720p', '1080p', '4k'] },
  { value: 'seedance-2-fast', label: 'Seedance 2 Fast', resolutions: ['480p', '720p'] },
  { value: 'seedance-2-mini', label: 'Seedance 2 Mini', resolutions: ['480p', '720p'], durations: [4, 8, 10, 12, 15] },
]
const references = computed(() => store.incomingNodes(props.nodeId))
const imageReferences = computed(() => references.value.filter((node) => node.type === 'image' && node.data.asset))
const promptParts = computed(() => props.data.promptParts ?? (props.data.prompt ? [{ type: 'text', value: props.data.prompt }] : []))
const selectedImageSettings = computed(() => normalizeImageSettings(props.data))
const selectedImageModel = computed(() => selectedImageSettings.value.model)
const selectedResolution = computed(() => props.type === 'image' ? selectedImageSettings.value.resolution : props.data.resolution || '720p')
const selectedAspectRatio = computed(() => props.type === 'image' ? selectedImageSettings.value.aspectRatio : props.data.aspectRatio || '16:9')
const selectedDuration = computed(() => props.data.duration ?? 5)
const selectedVideoModel = computed(() => videoModels.find((model) => model.value === props.data.model) || videoModels[0])
const referenceError = computed(() => props.type === 'image' && selectedImageModel.value.maxReferences && imageReferences.value.length > selectedImageModel.value.maxReferences
  ? `当前模型最多支持 ${selectedImageModel.value.maxReferences} 张参考图片`
  : '')
const panelMessage = computed(() => notice.value || referenceError.value)
const settingLabel = computed(() => {
  if (props.type === 'image') return `${selectedAspectRatio.value} · ${selectedResolution.value}`
  if (props.type === 'video') return `${selectedAspectRatio.value === 'adaptive' ? '自适应' : selectedAspectRatio.value} · ${selectedResolution.value} · ${selectedDuration.value === 0 ? '自动' : `${selectedDuration.value}s`}`
  return mediaTypes[props.type].setting
})
const displayReferences = computed(() => {
  const counts = { text: 0, image: 0, video: 0, audio: 0 }
  return references.value.map((node) => ({ key: node.id, node, number: ++counts[node.type], label: `${mediaTypes[node.type].label}${counts[node.type]}` }))
})
const canSubmit = computed(() => {
  if (!props.data.prompt?.trim() || referenceError.value) return false
  if (props.type !== 'text') return true
  return references.value.some((node) => node.type === 'text' ? node.data.content?.trim() : node.data.asset)
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
  notice.value = props.type === 'image' ? '图片生成后端暂未接入' : '模型暂未接入'
}

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(16 / width, 16 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}

function updateImageSetting(key, value) {
  updateNodeData(props.nodeId, { [key]: value })
  if (key === 'aspectRatio') nextTick(() => requestAnimationFrame(updateSettingsPosition))
}

function updateImageModel(model) {
  const updates = { model: model.id }
  if (!model.resolutions.includes(selectedResolution.value)) updates.resolution = model.defaultResolution
  if (!model.aspectRatios.includes(selectedAspectRatio.value)) updates.aspectRatio = model.defaultAspectRatio
  if (!model.search) Object.assign(updates, { googleSearch: false, googleImageSearch: false })
  updateNodeData(props.nodeId, updates)
  modelOpen.value = false
}

function updateImageSearch(enabled) {
  updateNodeData(props.nodeId, enabled ? { googleSearch: true } : { googleSearch: false, googleImageSearch: false })
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

function updateMenuPosition(trigger, menu, style) {
  if (!trigger || !menu) return
  const panelRect = trigger.closest('.generation-panel').getBoundingClientRect()
  const triggerRect = trigger.getBoundingClientRect()
  const menuHeight = menu.offsetHeight
  const menuWidth = menu.offsetWidth
  const gap = 8
  const centeredLeft = triggerRect.left - panelRect.left + (triggerRect.width - menuWidth) / 2
  const left = Math.min(Math.max(0, centeredLeft), Math.max(0, panelRect.width - menuWidth))
  const top = triggerRect.top - menuHeight - gap >= 12
    ? triggerRect.top - panelRect.top - menuHeight - gap
    : triggerRect.bottom - panelRect.top + gap
  style.value = { left: `${left}px`, top: `${top}px` }
}

function updateSettingsPosition() {
  updateMenuPosition(settingsTrigger.value, settingsMenu.value, settingsStyle)
}

function toggleModelMenu() {
  modelOpen.value = !modelOpen.value
  settingsOpen.value = false
  if (modelOpen.value) nextTick(() => updateMenuPosition(modelTrigger.value, modelMenu.value, modelStyle))
}

function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  modelOpen.value = false
  if (settingsOpen.value) nextTick(updateSettingsPosition)
}

function closeSettings(event) {
  if (!event.target.closest('.media-settings-menu, .media-settings-trigger')) settingsOpen.value = false
  if (!event.target.closest('.model-menu, .model-select-trigger')) modelOpen.value = false
}

onMounted(() => window.addEventListener('pointerdown', closeSettings))
onBeforeUnmount(() => window.removeEventListener('pointerdown', closeSettings))
</script>

<template>
  <section v-if="data.assetSource !== 'upload' && (type !== 'text' || data.textMode === 'task')" class="generation-panel nodrag nowheel" @pointerdown.stop>
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
      @pointerdown="settingsOpen = false; modelOpen = false"
    />
    <textarea
      v-else
      :value="data.prompt"
      :placeholder="mediaTypes[type].placeholder"
      @input="updateTextPrompt"
      @pointerdown="settingsOpen = false; modelOpen = false"
    ></textarea>

    <div v-if="modelOpen && type === 'image'" ref="modelMenu" class="model-menu" :style="modelStyle" @pointerdown.stop>
      <button v-for="model in imageModels" :key="model.id" :class="{ active: selectedImageModel.id === model.id }" @click="updateImageModel(model)">
        <WandSparkles :size="15" />
        <span>{{ model.label }}</span>
      </button>
    </div>

    <div v-if="settingsOpen && ['image', 'video'].includes(type)" ref="settingsMenu" class="image-settings-menu media-settings-menu" :style="settingsStyle" @pointerdown.stop>
      <template v-if="type === 'image'">
        <h3>清晰度</h3>
        <div class="image-resolution-options">
          <button v-for="resolution in selectedImageModel.resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="updateImageSetting('resolution', resolution)">
            {{ resolution }}
          </button>
        </div>
        <h3>比例</h3>
        <div class="image-ratio-grid">
          <button v-for="ratio in selectedImageModel.aspectRatios" :key="ratio" :class="{ active: selectedAspectRatio === ratio }" @click="updateImageSetting('aspectRatio', ratio)">
            <span class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
            <strong>{{ ratio }}</strong>
          </button>
        </div>

        <template v-if="selectedImageModel.search">
          <h3>搜索增强</h3>
          <label class="setting-toggle-row">
            <span>Google 文字搜索</span>
            <input type="checkbox" :checked="selectedImageSettings.googleSearch" @change="updateImageSearch($event.target.checked)" />
          </label>
          <label class="setting-toggle-row" :class="{ disabled: !selectedImageSettings.googleSearch }">
            <span>Google 图片搜索</span>
            <input type="checkbox" :checked="selectedImageSettings.googleImageSearch" :disabled="!selectedImageSettings.googleSearch" @change="updateImageSetting('googleImageSearch', $event.target.checked)" />
          </label>
        </template>
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
        <label class="setting-toggle-row">
          <span>生成同步音频</span>
          <input type="checkbox" :checked="data.generateAudio ?? true" @change="updateVideoSetting('generateAudio', $event.target.checked)" />
        </label>
      </template>
    </div>

    <p v-if="panelMessage" class="panel-notice">{{ panelMessage }}</p>

    <footer>
      <button v-if="type === 'image'" ref="modelTrigger" class="model-select model-select-trigger" @click="toggleModelMenu">
        <WandSparkles :size="16" />{{ selectedImageModel.label }}<ChevronDown :size="14" :class="{ rotated: modelOpen }" />
      </button>
      <span v-else class="model-select"><WandSparkles :size="16" />{{ type === 'video' ? selectedVideoModel.label : data.model }}</span>
      <span v-if="type !== 'text'" class="panel-divider"></span>
      <button v-if="['image', 'video'].includes(type)" ref="settingsTrigger" class="image-settings-trigger media-settings-trigger" @click="toggleSettings">
        <component :is="type === 'video' ? VideoIcon : Image" :size="16" />{{ settingLabel }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
      </button>
      <span v-else-if="type !== 'text'" class="setting-select"><Image :size="16" />{{ settingLabel }}</span>
      <button class="run-task-button" :disabled="!canSubmit" title="执行" @click="submitTask"><ArrowUp :size="20" /></button>
    </footer>
  </section>
</template>
