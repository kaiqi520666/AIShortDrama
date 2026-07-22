<script setup>
import brandMark from '../../assets/mooncut-mark.svg'

defineProps({ to: { type: String, default: '/' } })
</script>

<template>
  <RouterLink class="app-brand" :to="to" aria-label="Mooncut 首页">
    <img class="app-brand__symbol" :src="brandMark" alt="" aria-hidden="true" />
    <strong>Mooncut</strong>
  </RouterLink>
</template>
