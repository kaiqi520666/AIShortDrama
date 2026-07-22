<script setup>
import GlobalConfirm from './components/global/GlobalConfirm.vue'
import GlobalLoading from './components/global/GlobalLoading.vue'
import GlobalPrompt from './components/global/GlobalPrompt.vue'
import GlobalToast from './components/global/GlobalToast.vue'
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" :key="route.fullPath" />
  </RouterView>
  <GlobalToast />
  <GlobalConfirm />
  <GlobalPrompt />
  <GlobalLoading />
</template>
