<script setup>
import { Download, LoaderCircle } from 'lucide-vue-next'
import AppButton from './AppButton.vue'
import AppModal from './AppModal.vue'

defineProps({
  src: { type: String, required: true },
  title: { type: String, default: '图片预览' },
  downloading: Boolean,
})
defineEmits(['close', 'download'])
</script>

<template>
  <AppModal :title="title" content-class="app-media-preview" @close="$emit('close')">
    <template #header-actions>
      <AppButton icon-only size="sm" :disabled="downloading" title="下载原图" aria-label="下载原图" @click="$emit('download')">
        <LoaderCircle v-if="downloading" class="media-action-spinner" :size="16" />
        <Download v-else :size="16" />
      </AppButton>
    </template>
    <div class="app-media-preview-stage">
      <img :src="src" :alt="title" referrerpolicy="no-referrer" />
    </div>
  </AppModal>
</template>
