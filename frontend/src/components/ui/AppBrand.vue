<script setup>
import { Clapperboard } from 'lucide-vue-next'

defineProps({ to: { type: String, default: '/' } })
</script>

<template>
  <RouterLink class="app-brand" :to="to" aria-label="Mooncut 首页">
    <span class="app-brand__symbol"><Clapperboard :size="19" /></span>
    <strong>Mooncut</strong>
  </RouterLink>
</template>
