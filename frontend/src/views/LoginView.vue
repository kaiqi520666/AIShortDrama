<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthFormShell from '../components/auth/AuthFormShell.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await authStore.login({ email: email.value, password: password.value })
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/workspaces'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '登录失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthFormShell title="登录" subtitle="继续进入你的工作台">
    <form class="auth-form" @submit.prevent="submit">
      <label>邮箱<input v-model.trim="email" type="email" autocomplete="email" required /></label>
      <label>密码<input v-model="password" type="password" autocomplete="current-password" minlength="8" maxlength="72" required /></label>
      <p v-if="errorMessage" class="auth-error">{{ errorMessage }}</p>
      <button type="submit" :disabled="submitting">{{ submitting ? '登录中…' : '登录' }}</button>
    </form>
    <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
  </AuthFormShell>
</template>
