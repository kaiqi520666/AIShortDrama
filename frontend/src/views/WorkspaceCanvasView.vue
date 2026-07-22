<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CanvasView from './CanvasView.vue'
import AppButton from '../components/ui/AppButton.vue'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspaces'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const errorMessage = ref('')
workspaceStore.close()

onMounted(async () => {
  try {
    await workspaceStore.open(route.params.id)
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '工作台打开失败'
  }
})

function leaveCanvas() {
  if (!authStore.user) workspaceStore.$reset()
  router.push(authStore.user ? '/workspaces' : '/')
}
</script>

<template>
  <CanvasView v-if="workspaceStore.current" :workspace="workspaceStore.current" @back="leaveCanvas" />
  <main v-else class="route-state">
    <p>{{ errorMessage || '正在加载工作台…' }}</p>
    <AppButton v-if="errorMessage" variant="primary" @click="router.push('/workspaces')">返回工作台</AppButton>
  </main>
</template>
