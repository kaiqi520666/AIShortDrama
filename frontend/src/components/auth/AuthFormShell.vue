<script setup>
import { Clapperboard } from 'lucide-vue-next'

defineProps({ title: { type: String, required: true }, subtitle: { type: String, required: true } })
</script>

<template>
  <main class="auth-page auth-form-page">
    <RouterLink class="workspace-brand auth-brand" to="/"><span class="brand-symbol"><Clapperboard :size="19" /></span><strong>Mooncut</strong></RouterLink>
    <section class="auth-form-shell">
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
      <slot />
    </section>
  </main>
</template>
