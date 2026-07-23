<script setup>
import { ArrowLeft, CircleAlert, Folder, LoaderCircle, LogOut, UserRound } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppButton from '../ui/AppButton.vue'
import AppThemeSwitch from '../ui/AppThemeSwitch.vue'

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
      <span class="project-control-separator"></span>
      <AppBrand />
      <span class="project-divider"></span>
      <span class="project-context"><Folder :size="14" /><span class="project-select">{{ workspaceName }}</span></span>
    </div>
    <div class="canvas-account">
      <AppThemeSwitch />
      <div v-if="saveStatus !== 'saved'" class="save-state" :class="saveStatus">
        <LoaderCircle v-if="saveStatus === 'saving'" :size="13" />
        <CircleAlert v-else :size="13" />
        <span>{{ saveStatus === 'saving' ? '保存中' : '保存失败' }}</span>
      </div>
      <AppButton class="canvas-user-button" size="sm" variant="soft" title="当前用户"><UserRound :size="15" /><span>{{ username }}</span></AppButton>
      <AppButton class="canvas-logout-button" size="sm" title="退出登录" @click="emit('logout')"><LogOut :size="15" /><span>退出</span></AppButton>
    </div>
  </header>
</template>
