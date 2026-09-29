<script setup>
import { useI18n } from 'vue-i18n'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import CanvasView from './CanvasView.vue'
import AppButton from '../../components/ui/AppButton.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalLoading } from '../../composables/useGlobalLoading'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useContentTemplatesStore } from '../../stores/contentTemplates'
import { useWorkspaceStore } from '../../stores/workspaces'
import { stopWorkspaceGenerationPolling } from '../../services/generationPolling'
import { useWorkspaceCanvasSession } from './useWorkspaceCanvasSession'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const capabilityStore = useModelCapabilitiesStore()
const contentTemplateStore = useContentTemplatesStore()
const workspaceStore = useWorkspaceStore()
const loading = useGlobalLoading()
const toast = useGlobalToast()
const canvas = ref(null)
const canvasReady = computed(() => workspaceStore.current
  && capabilityStore.capabilities
  && (workspaceStore.current.workspace_type !== 'ecommerce' || contentTemplateStore.templates))
let pendingWorkspace = null
workspaceStore.close()
const {
  loadError: errorMessage,
  load,
  finishLoading,
  dispose,
} = useWorkspaceCanvasSession({ workspaceStore, capabilityStore, contentTemplateStore, loading, toast })

async function openCanvas() {
  await load(route.params.workspaceId, { initial: true })
}

onBeforeRouteUpdate(async (to) => {
  const workspaceId = to.params.workspaceId
  if (workspaceId === workspaceStore.current?.id) return true
  const canLeave = await canvas.value?.saveBeforeLeave?.()
  if (canLeave === false) return false
  const workspace = await load(workspaceId, { commit: false })
  if (!workspace) return false
  pendingWorkspace = workspace
  return true
})

watch(() => route.params.workspaceId, async (workspaceId) => {
  if (pendingWorkspace?.id === workspaceId) {
    const previousWorkspaceId = workspaceStore.current?.id
    if (previousWorkspaceId) stopWorkspaceGenerationPolling(previousWorkspaceId)
    workspaceStore.setCurrent(pendingWorkspace)
    pendingWorkspace = null
    return
  }
  if (workspaceStore.current?.id !== workspaceId) await load(workspaceId)
})

onMounted(openCanvas)
onBeforeUnmount(dispose)

function leaveCanvas() {
  if (!authStore.user) workspaceStore.$reset()
  router.push(authStore.user ? { name: 'workspaces' } : '/')
}
</script>

<template>
  <CanvasView v-if="canvasReady" ref="canvas" :key="workspaceStore.current.id" :workspace="workspaceStore.current" @back="leaveCanvas" @ready="finishLoading" />
  <main v-else-if="errorMessage" class="route-state">
    <EmptyState :title="t('canvas.canvasLoadFailed')" :description="errorMessage" tone="error">
      <AppButton variant="primary" @click="openCanvas">{{ t('canvas.reload') }}</AppButton>
      <AppButton @click="router.push({ name: 'workspaces' })">{{ t('canvas.backToWorkspace') }}</AppButton>
    </EmptyState>
  </main>
</template>
