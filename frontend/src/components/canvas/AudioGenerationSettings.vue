<script setup>
import AppSelect from '../ui/AppSelect.vue'
import AppSlider from '../ui/AppSlider.vue'

defineProps({
  settings: { type: Object, required: true },
  formatOptions: { type: Array, required: true },
  sampleRateOptions: { type: Array, required: true },
})
const emit = defineEmits(['update'])
</script>

<template>
  <div class="audio-setting-grid">
    <div>
      <span>格式</span>
      <AppSelect :model-value="settings.format" :options="formatOptions" aria-label="音频格式" @update:model-value="emit('update', 'format', $event)" />
    </div>
    <div>
      <span>采样率</span>
      <AppSelect class="audio-sample-select" :model-value="settings.sampleRate" :options="sampleRateOptions" aria-label="音频采样率" @update:model-value="emit('update', 'sampleRate', $event)" />
    </div>
  </div>
  <h3>声音调整</h3>
  <div class="audio-slider-list">
    <AppSlider :model-value="settings.speechRate" :min="-50" :max="100" label="语速" @update:model-value="emit('update', 'speechRate', $event)" />
    <AppSlider :model-value="settings.loudnessRate" :min="-50" :max="100" label="音量" @update:model-value="emit('update', 'loudnessRate', $event)" />
    <AppSlider :model-value="settings.pitchRate" :min="-12" :max="12" label="音调" @update:model-value="emit('update', 'pitchRate', $event)" />
  </div>
</template>
