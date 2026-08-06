<script setup>
import { ArrowLeft, Check, Folder, LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'
import AppBrand from '../ui/AppBrand.vue'
import AppButton from '../ui/AppButton.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

const props = defineProps({
  workspaceName: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
  saveStatus: { type: String, default: 'saved' },
})
const emit = defineEmits(['back', 'logout', 'retry-save'])
const saveState = computed(() => ({
  saved: { label: '已保存', icon: Check },
  saving: { label: '保存中', icon: LoaderCircle },
  failed: { label: '保存失败', icon: TriangleAlert },
  conflict: { label: '保存冲突', icon: TriangleAlert },
}[props.saveStatus] || { label: '已保存', icon: Check }))
</script>

<template>
  <header class="canvas-header">
    <div class="project-control">
      <AppButton class="project-back" icon-only size="sm" title="返回工作台" @click="emit('back')"><ArrowLeft :size="17" /></AppButton>
      <span class="project-control-separator"></span>
      <AppBrand />
      <span class="project-divider"></span>
      <span class="project-context"><Folder :size="14" /><span class="project-select">{{ workspaceName }}</span></span>
      <span class="canvas-save-state" :class="`is-${saveStatus}`" aria-live="polite">
        <component :is="saveState.icon" :size="13" :class="{ spinning: saveStatus === 'saving' }" />
        <span>{{ saveState.label }}</span>
        <AppButton v-if="saveStatus === 'failed'" icon-only size="sm" title="重新保存" @click="emit('retry-save')"><RefreshCw :size="13" /></AppButton>
      </span>
    </div>
    <AppHeaderAccountControls
      :username="username"
      :credit-balance="creditBalance"
      :credit-frozen="creditFrozen"
      @logout="emit('logout')"
    />
  </header>
</template>
