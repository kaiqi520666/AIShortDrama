<script setup>
import { Coins } from 'lucide-vue-next'

defineProps({
  balance: { type: Number, default: 0 },
  frozen: { type: Number, default: 0 },
})
</script>

<template>
  <span class="app-credit-balance" :title="`冻结积分 ${frozen}`" :aria-label="`可用积分 ${balance}，冻结积分 ${frozen}`">
    <Coins :size="15" />{{ balance }}
  </span>
</template>
