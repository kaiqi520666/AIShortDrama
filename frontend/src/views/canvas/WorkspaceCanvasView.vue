<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CanvasView from './CanvasView.vue'
import AppButton from '../../components/ui/AppButton.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalLoading } from '../../composables/useGlobalLoading'
import { useAuthStore } from '../../stores/auth'
import { useModelCapabilitiesStore } from '../../stores/modelCapabilities'
import { useWorkspaceStore } from '../../stores/workspaces'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const capabilityStore = useModelCapabilitiesStore()
const workspaceStore = useWorkspaceStore()
const loading = useGlobalLoading()
const errorMessage = ref('')
let loadingId = null
workspaceStore.close()

function finishLoading() {
  if (!loadingId) return
  loading.hideLoading(loadingId)
  loadingId = null
}

async function openCanvas() {
  loadingId = loading.showLoading('正在打开工作台…')
  errorMessage.value = ''
  try {
    await Promise.all([
      workspaceStore.open(route.params.workspaceId),
      capabilityStore.load(),
    ])
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '画布配置加载失败'
    finishLoading()
  }
}

onMounted(openCanvas)
onBeforeUnmount(finishLoading)

function leaveCanvas() {
  if (!authStore.user) workspaceStore.$reset()
  router.push(authStore.user ? { name: 'workspaces' } : '/')
}
</script>

<template>
  <CanvasView v-if="workspaceStore.current && capabilityStore.capabilities" :workspace="workspaceStore.current" @back="leaveCanvas" @ready="finishLoading" />
  <main v-else-if="errorMessage" class="route-state">
    <EmptyState title="画布加载失败" :description="errorMessage" tone="error">
      <AppButton variant="primary" @click="openCanvas">重新加载</AppButton>
      <AppButton @click="router.push({ name: 'workspaces' })">返回工作台</AppButton>
    </EmptyState>
  </main>
</template>
