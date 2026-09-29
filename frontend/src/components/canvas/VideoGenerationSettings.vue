<script setup>
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import AppButton from '../ui/AppButton.vue'

const { t } = useI18n()

const props = defineProps({
  model: { type: Object, required: true },
  settings: { type: Object, required: true },
  selectedDuration: { type: Number, required: true },
  selectedResolution: { type: String, required: true },
  selectedAspectRatio: { type: String, required: true },
  storyboard: Boolean,
  segmentIndex: { type: Number, default: 1 },
  continuityMode: { type: String, default: 'extend' },
})
const emit = defineEmits(['update'])

const hasDurationOptions = computed(() => Boolean(props.model.durationOptions))

function ratioIconStyle(value) {
  const [width, height] = value.split(':').map(Number)
  const scale = Math.min(16 / width, 16 / height)
  return { width: `${Math.round(width * scale)}px`, height: `${Math.round(height * scale)}px` }
}
</script>

<template>
  <template v-if="storyboard && segmentIndex > 1">
    <h3>{{ t('canvas.continuity') }}</h3>
    <div class="video-duration-options">
      <AppButton :class="{ active: continuityMode === 'extend' }" @click="emit('update', 'continuityMode', 'extend')">{{ t('canvas.extend') }}</AppButton>
      <AppButton :class="{ active: continuityMode === 'cut' }" @click="emit('update', 'continuityMode', 'cut')">{{ t('canvas.cut') }}</AppButton>
    </div>
  </template>
  <h3>{{ t('canvas.duration') }}</h3>
  <div v-if="hasDurationOptions" class="video-duration-options">
    <AppButton v-for="duration in model.durationOptions" :key="duration" :class="{ active: selectedDuration === duration }" @click="emit('update', 'duration', duration)">{{ duration }}s</AppButton>
  </div>
  <div v-else class="video-duration-slider">
    <input type="range" :min="model.durationMin" :max="model.durationMax" step="1" :value="selectedDuration" :aria-label="t('canvas.videoDuration')" @input="emit('update', 'duration', Number($event.target.value))" />
    <span>{{ selectedDuration }}s</span>
  </div>

  <h3>{{ t('canvas.resolution') }}</h3>
  <div class="image-resolution-options">
    <AppButton v-for="resolution in model.resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="emit('update', 'resolution', resolution)">{{ resolution === '4k' ? '4K' : resolution }}</AppButton>
  </div>

  <h3>{{ t('canvas.ratio') }}</h3>
  <div class="image-ratio-grid video-ratio-grid">
    <AppButton v-for="ratio in model.aspectRatios" :key="ratio" :class="{ active: selectedAspectRatio === ratio }" @click="emit('update', 'aspectRatio', ratio)">
      <span class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
      <strong>{{ ratio }}</strong>
    </AppButton>
  </div>

  <template v-if="model.generateAudio">
    <h3>{{ t('canvas.output') }}</h3>
    <label class="setting-toggle-row">
      <span>{{ t('canvas.generateAudio') }}</span>
      <input type="checkbox" :checked="settings.generateAudio" @change="emit('update', 'generateAudio', $event.target.checked)" />
    </label>
  </template>
</template>
