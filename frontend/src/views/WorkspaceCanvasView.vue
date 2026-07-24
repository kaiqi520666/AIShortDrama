<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CanvasView from './CanvasView.vue'
import AppButton from '../components/ui/AppButton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useGlobalLoading } from '../composables/useGlobalLoading'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspaces'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
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

onMounted(async () => {
  loadingId = loading.showLoading('正在打开工作台…')
  try {
    await workspaceStore.open(route.params.workspaceId)
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '工作台打开失败'
    finishLoading()
  }
})
onBeforeUnmount(finishLoading)

function leaveCanvas() {
  if (!authStore.user) workspaceStore.$reset()
  router.push(authStore.user ? { name: 'workspaces' } : '/')
}
</script>

<template>
  <CanvasView v-if="workspaceStore.current" :workspace="workspaceStore.current" @back="leaveCanvas" @ready="finishLoading" />
  <main v-else-if="errorMessage" class="route-state">
    <EmptyState title="工作台打开失败" :description="errorMessage" tone="error">
      <AppButton variant="primary" @click="router.push({ name: 'workspaces' })">返回工作台</AppButton>
    </EmptyState>
  </main>
</template>
