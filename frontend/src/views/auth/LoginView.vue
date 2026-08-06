<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, CircleAlert, LockKeyhole, Mail } from 'lucide-vue-next'
import AuthFormShell from '../../components/auth/AuthFormShell.vue'
import AuthInputField from '../../components/auth/AuthInputField.vue'
import AppButton from '../../components/ui/AppButton.vue'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

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
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/dashboard/workspaces'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthFormShell title="登录" subtitle="继续进入你的工作台">
    <form class="auth-form" @submit.prevent="submit">
      <AuthInputField v-model.trim="email" label="邮箱" :icon="Mail" type="email" autocomplete="email" required />
      <AuthInputField v-model="password" label="密码" :icon="LockKeyhole" type="password" autocomplete="current-password" minlength="8" maxlength="72" revealable required />
      <p v-if="errorMessage" class="auth-error"><CircleAlert :size="14" />{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting"><span>{{ submitting ? '登录中…' : '登录' }}</span><ArrowRight :size="17" /></AppButton>
    </form>
    <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
  </AuthFormShell>
</template>
