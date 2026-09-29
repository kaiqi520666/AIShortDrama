<script setup>
import { Download, LoaderCircle } from 'lucide-vue-next'
import AppButton from './AppButton.vue'
import AppModal from './AppModal.vue'

defineProps({
  src: { type: String, required: true },
  title: { type: String, default: '' },
  downloading: Boolean,
})
defineEmits(['close', 'download'])
</script>

<template>
  <AppModal :title="title || $t('canvas.previewOriginal')" content-class="app-media-preview" @close="$emit('close')">
    <template #header-actions>
      <AppButton icon-only size="sm" :disabled="downloading" :title="$t('canvas.downloadOriginal')" :aria-label="$t('canvas.downloadOriginal')" @click="$emit('download')">
        <LoaderCircle v-if="downloading" class="media-action-spinner" :size="16" />
        <Download v-else :size="16" />
      </AppButton>
    </template>
    <div class="app-media-preview-stage">
      <img :src="src" :alt="title" referrerpolicy="no-referrer" />
    </div>
  </AppModal>
</template>
