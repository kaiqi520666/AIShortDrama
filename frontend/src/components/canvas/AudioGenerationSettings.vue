<script setup>
import { useI18n } from 'vue-i18n'
import AppSelect from '../ui/AppSelect.vue'
import AppSlider from '../ui/AppSlider.vue'

const { t } = useI18n()

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
      <span>{{ t('canvas.format') }}</span>
      <AppSelect :model-value="settings.format" :options="formatOptions" :aria-label="t('canvas.audioFormat')" @update:model-value="emit('update', 'format', $event)" />
    </div>
    <div>
      <span>{{ t('canvas.sampleRate') }}</span>
      <AppSelect class="audio-sample-select" :model-value="settings.sampleRate" :options="sampleRateOptions" :aria-label="t('canvas.audioSampleRate')" @update:model-value="emit('update', 'sampleRate', $event)" />
    </div>
  </div>
  <h3>{{ t('canvas.voiceAdjustment') }}</h3>
  <div class="audio-slider-list">
    <AppSlider :model-value="settings.speechRate" :min="-50" :max="100" :label="t('canvas.speechRate')" @update:model-value="emit('update', 'speechRate', $event)" />
    <AppSlider :model-value="settings.loudnessRate" :min="-50" :max="100" :label="t('canvas.volume')" @update:model-value="emit('update', 'loudnessRate', $event)" />
    <AppSlider :model-value="settings.pitchRate" :min="-12" :max="12" :label="t('canvas.pitch')" @update:model-value="emit('update', 'pitchRate', $event)" />
  </div>
</template>
