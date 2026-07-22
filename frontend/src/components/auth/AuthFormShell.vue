<script setup>
import { Clapperboard, ShieldCheck } from 'lucide-vue-next'

defineProps({ title: { type: String, required: true }, subtitle: { type: String, required: true } })
</script>

<template>
  <main class="auth-page auth-form-page">
    <RouterLink class="workspace-brand auth-brand" to="/"><span class="brand-symbol"><Clapperboard :size="19" /></span><strong>Mooncut</strong></RouterLink>
    <section class="auth-form-shell">
      <header class="auth-form-header">
        <span class="auth-form-mark"><ShieldCheck :size="20" /></span>
        <div><h1>{{ title }}</h1><p>{{ subtitle }}</p></div>
      </header>
      <slot />
    </section>
  </main>
</template>
