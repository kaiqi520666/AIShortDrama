<script setup>
import brandMark from '../../assets/mooncut-mark.svg'

defineProps({
  to: { type: String, default: '/' },
  iconOnly: Boolean,
})
</script>

<template>
  <RouterLink class="app-brand" :to="to" :aria-label="$t('common.brandHome')">
    <img class="app-brand__symbol" :src="brandMark" alt="" aria-hidden="true" />
    <strong v-if="!iconOnly">Mooncut</strong>
  </RouterLink>
</template>
