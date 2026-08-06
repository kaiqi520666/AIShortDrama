<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import CanvasView from './CanvasView.vue'
import AppButton from '../../components/ui/AppButton.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalLoading } from '../../composables/useGlobalLoading'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useWorkspaceStore } from '../../stores/workspaces'
import { stopWorkspaceGenerationPolling } from '../../services/generationPolling'
import { useWorkspaceCanvasSession } from './useWorkspaceCanvasSession'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const capabilityStore = useModelCapabilitiesStore()
const workspaceStore = useWorkspaceStore()
const loading = useGlobalLoading()
const toast = useGlobalToast()
const canvas = ref(null)
let pendingWorkspace = null
workspaceStore.close()
const {
  loadError: errorMessage,
  load,
  finishLoading,
  dispose,
} = useWorkspaceCanvasSession({ workspaceStore, capabilityStore, loading, toast })

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
  <CanvasView v-if="workspaceStore.current && capabilityStore.capabilities" ref="canvas" :key="workspaceStore.current.id" :workspace="workspaceStore.current" @back="leaveCanvas" @ready="finishLoading" />
  <main v-else-if="errorMessage" class="route-state">
    <EmptyState title="画布加载失败" :description="errorMessage" tone="error">
      <AppButton variant="primary" @click="openCanvas">重新加载</AppButton>
      <AppButton @click="router.push({ name: 'workspaces' })">返回工作台</AppButton>
    </EmptyState>
  </main>
</template>
