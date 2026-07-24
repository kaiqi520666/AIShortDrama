<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useWorkspaceStore } from '../../stores/workspaces'
import AppDashboardShell from './AppDashboardShell.vue'

defineProps({ activeItem: { type: String, required: true } })
const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()

async function signOut() {
  await authStore.logout()
  workspaceStore.$reset()
  await router.replace('/')
}
</script>

<template>
  <AppDashboardShell :active-item="activeItem" :username="authStore.user?.username || '用户'" @logout="signOut">
    <slot />
  </AppDashboardShell>
</template>
