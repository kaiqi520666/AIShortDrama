<script setup>
import { ArrowLeft, Clapperboard, GitBranch, LoaderCircle } from 'lucide-vue-next'

defineProps({
  workspaceName: { type: String, required: true },
  saveStatus: { type: String, required: true },
})
const emit = defineEmits(['back'])
</script>

<template>
  <header class="canvas-header">
    <div class="project-control">
      <button class="project-back" title="返回工作台" @click="emit('back')"><ArrowLeft :size="17" /></button>
      <div class="brand-mark"><Clapperboard :size="19" /></div>
      <span class="project-name">Mooncut</span>
      <span class="project-divider"></span>
      <span class="project-select">{{ workspaceName }}</span>
    </div>

    <div class="view-switch" role="tablist" aria-label="项目视图">
      <span class="active"><GitBranch :size="14" />工作流</span>
    </div>
    <div class="save-state" :class="saveStatus">
      <LoaderCircle v-if="saveStatus === 'saving'" :size="13" />
      {{ saveStatus === 'saving' ? '保存中' : saveStatus === 'failed' ? '保存失败' : '已保存' }}
    </div>
  </header>
</template>
