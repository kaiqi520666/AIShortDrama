<script setup>
import { ArrowLeft, Folder } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppButton from '../ui/AppButton.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

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
    <AppHeaderAccountControls
      :username="username"
      :credit-balance="creditBalance"
      :credit-frozen="creditFrozen"
      @logout="emit('logout')"
    />
  </header>
</template>
