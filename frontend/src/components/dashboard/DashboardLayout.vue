<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useWorkspaceStore } from '../../stores/workspaces'
import AppDashboardShell from './AppDashboardShell.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const activeItem = computed(() => route.meta.navKey)

async function signOut() {
  await authStore.logout()
  workspaceStore.$reset()
  await router.replace('/')
}
</script>

<template>
  <AppDashboardShell :active-item="activeItem" :username="authStore.user?.username || '用户'" @logout="signOut">
    <RouterView />
  </AppDashboardShell>
</template>
