<script setup>
import { ShieldCheck } from 'lucide-vue-next'
import AppBrand from '../ui/AppBrand.vue'
import AppLanguageSelect from '../ui/AppLanguageSelect.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, required: true },
})
</script>

<template>
  <main class="auth-page auth-form-page">
    <div class="auth-language"><AppLanguageSelect /></div>
    <div class="auth-form-stack">
      <AppBrand class="auth-brand" icon-only />
      <section class="auth-form-shell">
        <header class="auth-form-header">
          <span class="auth-form-mark"><ShieldCheck :size="20" /></span>
          <div><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>
        </header>
        <slot />
      </section>
    </div>
  </main>
</template>

<style scoped>
.auth-language { position: absolute; top: 20px; right: 20px; z-index: 2; }
</style>
