<script setup>
import { ArrowLeft, Clapperboard, GitBranch, LoaderCircle, LogOut } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

defineProps({
  workspaceName: { type: String, required: true },
  saveStatus: { type: String, required: true },
  username: { type: String, required: true },
})
const emit = defineEmits(['back', 'logout'])
</script>

<template>
  <header class="canvas-header">
    <div class="project-control">
      <AppButton class="project-back" icon-only size="sm" title="返回工作台" @click="emit('back')"><ArrowLeft :size="17" /></AppButton>
      <div class="brand-mark"><Clapperboard :size="18" /></div>
      <span class="project-name">Mooncut</span>
      <span class="project-divider"></span>
      <span class="project-select">{{ workspaceName }}</span>
    </div>

    <div class="view-switch" role="tablist" aria-label="项目视图">
      <span class="active"><GitBranch :size="14" />工作流</span>
    </div>
    <div class="canvas-account">
      <div class="save-state" :class="saveStatus">
        <LoaderCircle v-if="saveStatus === 'saving'" :size="13" />
        {{ saveStatus === 'saving' ? '保存中' : saveStatus === 'failed' ? '保存失败' : '已保存' }}
      </div>
      <span>{{ username }}</span>
      <AppButton icon-only size="sm" title="退出登录" @click="emit('logout')"><LogOut :size="15" /></AppButton>
    </div>
  </header>
</template>
