<script setup>
import AppAccountMenu from '../account/AppAccountMenu.vue'
import AppCreditBalance from './AppCreditBalance.vue'
import AppThemeSwitch from './AppThemeSwitch.vue'
import AppLanguageSelect from './AppLanguageSelect.vue'

defineProps({
  username: { type: String, required: true },
  creditBalance: { type: Number, default: 0 },
  creditFrozen: { type: Number, default: 0 },
})
const emit = defineEmits(['logout'])
</script>

<template>
  <div class="app-header-account-controls">
    <AppThemeSwitch />
    <AppLanguageSelect />
    <AppCreditBalance :balance="creditBalance" :frozen="creditFrozen" />
    <AppAccountMenu :username="username" @logout="emit('logout')" />
  </div>
</template>
