<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUp, ChevronDown, Coins, Image, LoaderCircle } from 'lucide-vue-next'
import { getImageModel, normalizeImageSettings } from '../../config/imageModels'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import AppButton from '../ui/AppButton.vue'
import AppMenu from '../ui/AppMenu.vue'

const props = defineProps({
  settings: { type: Object, required: true },
  estimatedCredits: { type: Number, required: true },
  disabled: Boolean,
  running: Boolean,
  submitLabel: { type: String, default: '生成图片' },
})
const emit = defineEmits(['update:settings', 'submit'])

const capabilityStore = useModelCapabilitiesStore()
const imageModels = computed(() => capabilityStore.imageModels)
const defaultImageModel = computed(() => capabilityStore.defaultImageModel)
const normalized = computed(() => normalizeImageSettings(props.settings, imageModels.value, defaultImageModel.value))
const model = computed(() => normalized.value.model)
const modelOpen = ref(false)
const settingsOpen = ref(false)
const modelTrigger = ref(null)
const modelMenu = ref(null)
const settingsTrigger = ref(null)
const settingsMenu = ref(null)
const modelStyle = ref({})
const settingsStyle = ref({})

function getElement(target) {
  return target?.element || target?.$el || target
}

function updateMenuPosition(trigger, menu, style) {
  const triggerElement = getElement(trigger)
  const menuElement = getElement(menu)
  if (!triggerElement || !menuElement) return
  const panelRect = triggerElement.closest('.generation-panel').getBoundingClientRect()
  const triggerRect = triggerElement.getBoundingClientRect()
  const gap = 8
  const left = Math.min(Math.max(0, triggerRect.left - panelRect.left), Math.max(0, panelRect.width - menuElement.offsetWidth))
  const top = triggerRect.top - menuElement.offsetHeight - gap >= 12
    ? triggerRect.top - panelRect.top - menuElement.offsetHeight - gap
    : triggerRect.bottom - panelRect.top + gap
  style.value = { left: `${left}px`, top: `${top}px` }
}

function toggleModelMenu() {
  modelOpen.value = !modelOpen.value
  settingsOpen.value = false
  if (modelOpen.value) nextTick(() => updateMenuPosition(modelTrigger.value, modelMenu.value, modelStyle))
}

function toggleSettings() {
  settingsOpen.value = !settingsOpen.value
  modelOpen.value = false
  if (settingsOpen.value) nextTick(() => updateMenuPosition(settingsTrigger.value, settingsMenu.value, settingsStyle))
}

function updateModel(modelId) {
  const nextModel = getImageModel(imageModels.value, defaultImageModel.value, modelId)
  emit('update:settings', {
    model: nextModel.id,
    resolution: nextModel.resolutions.includes(normalized.value.resolution) ? normalized.value.resolution : nextModel.defaultResolution,
    aspectRatio: nextModel.aspectRatios.includes(normalized.value.aspectRatio) ? normalized.value.aspectRatio : nextModel.defaultAspectRatio,
    ...(!nextModel.search ? { googleSearch: false, googleImageSearch: false } : {}),
  })
  modelOpen.value = false
}

function updateSetting(key, value) {
  emit('update:settings', { [key]: value })
  if (['resolution', 'aspectRatio'].includes(key)) settingsOpen.value = false
  if (key === 'aspectRatio') nextTick(() => updateMenuPosition(settingsTrigger.value, settingsMenu.value, settingsStyle))
}

function updateSearch(enabled) {
  emit('update:settings', enabled ? { googleSearch: true } : { googleSearch: false, googleImageSearch: false })
}

function closeMenus(event) {
  if (!event.target.closest('.media-settings-menu, .media-settings-trigger')) settingsOpen.value = false
  if (!event.target.closest('.model-menu, .model-select-trigger')) modelOpen.value = false
}

function handleKeydown(event) {
  if (event.key !== 'Escape') return
  if (!settingsOpen.value && !modelOpen.value) return
  event.preventDefault()
  settingsOpen.value = false
  modelOpen.value = false
}

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(16 / width, 16 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}

onMounted(() => {
  window.addEventListener('pointerdown', closeMenus)
  window.addEventListener('keydown', handleKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', closeMenus)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <footer>
    <AppMenu v-if="modelOpen" ref="modelMenu" class="model-menu" :style="modelStyle" @pointerdown.stop>
      <AppButton v-for="option in imageModels" :key="option.id" :class="{ active: model.id === option.id }" @click="updateModel(option.id)">
        <Image :size="15" /><span>{{ option.label }}</span>
      </AppButton>
    </AppMenu>

    <AppMenu v-if="settingsOpen" ref="settingsMenu" class="image-settings-menu media-settings-menu" :style="settingsStyle" @pointerdown.stop>
      <h3>清晰度</h3>
      <div class="image-resolution-options">
        <AppButton v-for="value in model.resolutions" :key="value" :class="{ active: normalized.resolution === value }" @click="updateSetting('resolution', value)">{{ value }}</AppButton>
      </div>
      <h3>比例</h3>
      <div class="image-ratio-grid">
        <AppButton v-for="value in model.aspectRatios" :key="value" :class="{ active: normalized.aspectRatio === value }" @click="updateSetting('aspectRatio', value)">
          <span class="image-ratio-icon" :style="ratioIconStyle(value)"></span><strong>{{ value }}</strong>
        </AppButton>
      </div>
      <template v-if="model.search">
        <h3>搜索增强</h3>
        <label class="setting-toggle-row"><span>Google 文字搜索</span><input type="checkbox" :checked="normalized.googleSearch" @change="updateSearch($event.target.checked)" /></label>
        <label class="setting-toggle-row" :class="{ disabled: !normalized.googleSearch }"><span>Google 图片搜索</span><input type="checkbox" :checked="normalized.googleImageSearch" :disabled="!normalized.googleSearch" @change="updateSetting('googleImageSearch', $event.target.checked)" /></label>
      </template>
    </AppMenu>

    <AppButton ref="modelTrigger" class="model-select model-select-trigger" aria-label="图片模型" @click="toggleModelMenu">
      <Image :size="16" />{{ model.label }}<ChevronDown :size="14" :class="{ rotated: modelOpen }" />
    </AppButton>
    <span class="panel-divider"></span>
    <AppButton ref="settingsTrigger" class="image-settings-trigger media-settings-trigger" aria-label="图片规格" @click="toggleSettings">
      <Image :size="16" />{{ normalized.aspectRatio }} · {{ normalized.resolution }}<ChevronDown :size="14" :class="{ rotated: settingsOpen }" />
    </AppButton>
    <span class="task-credit-cost"><Coins :size="14" />本次 {{ estimatedCredits }} 积分</span>
    <AppButton class="run-task-button" icon-only variant="primary" :disabled="disabled" :title="running ? '执行中' : submitLabel" @click="emit('submit')">
      <LoaderCircle v-if="running" class="run-task-spinner" :size="20" /><ArrowUp v-else :size="20" />
    </AppButton>
  </footer>
</template>
