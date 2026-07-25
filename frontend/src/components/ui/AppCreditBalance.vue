<script setup>
import { Coins } from 'lucide-vue-next'

defineProps({
  balance: { type: Number, default: 0 },
  frozen: { type: Number, default: 0 },
})
</script>

<template>
  <RouterLink :to="{ name: 'recharge' }" class="app-credit-balance" :title="`冻结积分 ${frozen}`" :aria-label="`可用积分 ${balance}，冻结积分 ${frozen}，前往充值`">
    <Coins :size="15" />{{ balance }}
  </RouterLink>
</template>
