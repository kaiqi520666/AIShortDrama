<script setup>
import { onMounted, ref } from 'vue'
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
workspaceStore.close()

onMounted(async () => {
  const loadingId = loading.showLoading('正在打开工作台…')
  try {
    await workspaceStore.open(route.params.id)
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '工作台打开失败'
  } finally {
    loading.hideLoading(loadingId)
  }
})

function leaveCanvas() {
  if (!authStore.user) workspaceStore.$reset()
  router.push(authStore.user ? '/workspaces' : '/')
}
</script>

<template>
  <CanvasView v-if="workspaceStore.current" :workspace="workspaceStore.current" @back="leaveCanvas" />
  <main v-else-if="errorMessage" class="route-state">
    <EmptyState title="工作台打开失败" :description="errorMessage" tone="error">
      <AppButton variant="primary" @click="router.push('/workspaces')">返回工作台</AppButton>
    </EmptyState>
  </main>
</template>
