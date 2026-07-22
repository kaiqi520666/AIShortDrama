<script setup>
import GlobalConfirm from './components/global/GlobalConfirm.vue'
import GlobalLoading from './components/global/GlobalLoading.vue'
import GlobalToast from './components/global/GlobalToast.vue'
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" :key="route.fullPath" />
  </RouterView>
  <GlobalToast />
  <GlobalConfirm />
  <GlobalLoading />
</template>
