<script setup>
import { computed } from 'vue'
import AppButton from '../ui/AppButton.vue'

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
    <h3>衔接方式</h3>
    <div class="video-duration-options">
      <AppButton :class="{ active: continuityMode === 'extend' }" @click="emit('update', 'continuityMode', 'extend')">向后延长</AppButton>
      <AppButton :class="{ active: continuityMode === 'cut' }" @click="emit('update', 'continuityMode', 'cut')">独立换场</AppButton>
    </div>
  </template>
  <h3>时长</h3>
  <div v-if="hasDurationOptions" class="video-duration-options">
    <AppButton v-for="duration in model.durationOptions" :key="duration" :class="{ active: selectedDuration === duration }" @click="emit('update', 'duration', duration)">{{ duration }}s</AppButton>
  </div>
  <div v-else class="video-duration-slider">
    <input type="range" :min="model.durationMin" :max="model.durationMax" step="1" :value="selectedDuration" aria-label="视频时长" @input="emit('update', 'duration', Number($event.target.value))" />
    <span>{{ selectedDuration }}s</span>
  </div>

  <h3>清晰度</h3>
  <div class="image-resolution-options">
    <AppButton v-for="resolution in model.resolutions" :key="resolution" :class="{ active: selectedResolution === resolution }" @click="emit('update', 'resolution', resolution)">{{ resolution === '4k' ? '4K' : resolution }}</AppButton>
  </div>

  <h3>比例</h3>
  <div class="image-ratio-grid video-ratio-grid">
    <AppButton v-for="ratio in model.aspectRatios" :key="ratio" :class="{ active: selectedAspectRatio === ratio }" @click="emit('update', 'aspectRatio', ratio)">
      <span class="image-ratio-icon" :style="ratioIconStyle(ratio)"></span>
      <strong>{{ ratio }}</strong>
    </AppButton>
  </div>

  <template v-if="model.generateAudio">
    <h3>输出</h3>
    <label class="setting-toggle-row">
      <span>生成同步音频</span>
      <input type="checkbox" :checked="settings.generateAudio" @change="emit('update', 'generateAudio', $event.target.checked)" />
    </label>
  </template>
</template>
