<script setup>
import { ArrowLeft, Folder } from 'lucide-vue-next'
import AppAccountMenu from '../account/AppAccountMenu.vue'
import AppBrand from '../ui/AppBrand.vue'
import AppButton from '../ui/AppButton.vue'
import AppCreditBalance from '../ui/AppCreditBalance.vue'
import AppThemeSwitch from '../ui/AppThemeSwitch.vue'

defineProps({
  workspaceName: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
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
      <AppCreditBalance :balance="creditBalance" :frozen="creditFrozen" />
      <AppAccountMenu :username="username" @logout="emit('logout')" />
    </div>
  </header>
</template>
