<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, CircleAlert, LockKeyhole, Mail, UserRound } from 'lucide-vue-next'
import AuthFormShell from '../../components/auth/AuthFormShell.vue'
import AuthInputField from '../../components/auth/AuthInputField.vue'
import AppButton from '../../components/ui/AppButton.vue'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

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
    await router.replace({ name: 'workspaces' })
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '注册失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthFormShell title="创建账号" subtitle="注册后即可开始创建工作台">
    <form class="auth-form" @submit.prevent="submit">
      <AuthInputField v-model.trim="username" label="用户名" :icon="UserRound" autocomplete="username" minlength="2" maxlength="32" required />
      <AuthInputField v-model.trim="email" label="邮箱" :icon="Mail" type="email" autocomplete="email" required />
      <AuthInputField v-model="password" label="密码" :icon="LockKeyhole" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
      <p v-if="errorMessage" class="auth-error"><CircleAlert :size="14" />{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting"><span>{{ submitting ? '注册中…' : '注册并登录' }}</span><ArrowRight :size="17" /></AppButton>
    </form>
    <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
  </AuthFormShell>
</template>
