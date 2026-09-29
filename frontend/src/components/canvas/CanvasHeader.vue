<script setup>
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Check, Folder, LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'
import AppBrand from '../ui/AppBrand.vue'
import AppButton from '../ui/AppButton.vue'
import AppHeaderAccountControls from '../ui/AppHeaderAccountControls.vue'

const { t } = useI18n()

const props = defineProps({
  workspaceName: { type: String, required: true },
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
  saveStatus: { type: String, default: 'saved' },
})
const emit = defineEmits(['back', 'logout', 'retry-save'])
const saveState = computed(() => ({
  saved: { label: t('canvas.saved'), icon: Check },
  saving: { label: t('canvas.saving'), icon: LoaderCircle },
  failed: { label: t('canvas.saveFailed'), icon: TriangleAlert },
  conflict: { label: t('canvas.saveConflict'), icon: TriangleAlert },
}[props.saveStatus] || { label: t('canvas.saved'), icon: Check }))
</script>

<template>
  <header class="canvas-header">
    <div class="project-control">
      <AppButton class="project-back" icon-only size="sm" :title="t('canvas.backToWorkspace')" @click="emit('back')"><ArrowLeft :size="17" /></AppButton>
      <span class="project-control-separator"></span>
      <AppBrand />
      <span class="project-divider"></span>
      <span class="project-context"><Folder :size="14" /><span class="project-select">{{ workspaceName }}</span></span>
      <span class="canvas-save-state" :class="`is-${saveStatus}`" :title="saveState.label" aria-live="polite">
        <component :is="saveState.icon" :size="13" :class="{ spinning: saveStatus === 'saving' }" />
        <span>{{ saveState.label }}</span>
        <AppButton v-if="saveStatus === 'failed'" icon-only size="sm" :title="t('canvas.retrySave')" @click="emit('retry-save')"><RefreshCw :size="13" /></AppButton>
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
