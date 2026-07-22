<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthFormShell from '../components/auth/AuthFormShell.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppInput from '../components/ui/AppInput.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await authStore.register({ username: username.value, email: email.value, password: password.value })
    await router.replace('/workspaces')
  } catch (error) {
    errorMessage.value = error.response?.data?.message || error.message || '注册失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthFormShell title="创建账号" subtitle="注册后即可开始创建工作台">
    <form class="auth-form" @submit.prevent="submit">
      <label>用户名<AppInput v-model.trim="username" type="text" autocomplete="username" minlength="2" maxlength="32" required /></label>
      <label>邮箱<AppInput v-model.trim="email" type="email" autocomplete="email" required /></label>
      <label>密码<AppInput v-model="password" type="password" autocomplete="new-password" minlength="8" maxlength="72" required /></label>
      <p v-if="errorMessage" class="auth-error">{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting">{{ submitting ? '注册中…' : '注册并登录' }}</AppButton>
    </form>
    <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
  </AuthFormShell>
</template>
