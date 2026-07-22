<script setup>
import { ref } from 'vue'
import CanvasView from './views/CanvasView.vue'
import WorkspaceHome from './views/WorkspaceHome.vue'
import { useWorkspaceStore } from './stores/workspaces'

const workspaceStore = useWorkspaceStore()
const notice = ref('')

async function openWorkspace(id) {
  notice.value = ''
  try {
    await workspaceStore.open(id)
  } catch (error) {
    notice.value = error.response?.data?.message || error.message || '工作台打开失败'
  }
}
</script>

<template>
  <CanvasView v-if="workspaceStore.current" :workspace="workspaceStore.current" @back="workspaceStore.close()" />
  <WorkspaceHome v-else @open="openWorkspace" />
  <p v-if="notice" class="app-notice">{{ notice }}</p>
</template>
