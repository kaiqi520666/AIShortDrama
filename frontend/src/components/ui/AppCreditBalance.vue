<script setup>
import { Coins } from 'lucide-vue-next'

defineProps({
  balance: { type: Number, default: 0 },
  frozen: { type: Number, default: 0 },
})
</script>

<template>
  <RouterLink :to="{ name: 'recharge' }" class="app-credit-balance" :title="$t('account.frozenCount', { count: $n(frozen) })" :aria-label="$t('account.balanceAria', { balance: $n(balance), frozen: $n(frozen) })">
    <Coins :size="15" />{{ $n(balance) }}
  </RouterLink>
</template>
