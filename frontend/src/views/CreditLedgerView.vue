<script setup>
import CreditLedgerPanel from '../components/account/CreditLedgerPanel.vue'
import DashboardPageShell from '../components/dashboard/DashboardPageShell.vue'
</script>

<template>
  <DashboardPageShell active-item="credits">
    <section class="account-content"><CreditLedgerPanel /></section>
  </DashboardPageShell>
</template>
