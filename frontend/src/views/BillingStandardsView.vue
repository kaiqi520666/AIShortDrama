<script setup>
import BillingStandardsPanel from '../components/account/BillingStandardsPanel.vue'
import DashboardPageShell from '../components/dashboard/DashboardPageShell.vue'
</script>

<template>
  <DashboardPageShell active-item="pricing">
    <section class="account-content"><BillingStandardsPanel /></section>
  </DashboardPageShell>
</template>
