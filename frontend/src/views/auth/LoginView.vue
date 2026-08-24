<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, CircleAlert, LockKeyhole, Mail } from 'lucide-vue-next'
import AuthFormShell from '../../components/auth/AuthFormShell.vue'
import AuthInputField from '../../components/auth/AuthInputField.vue'
import TurnstileWidget from '../../components/auth/TurnstileWidget.vue'
import AppButton from '../../components/ui/AppButton.vue'
import { getCaptchaConfig } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)
const captchaRequired = ref(false)
const siteKey = ref('')
const captchaToken = ref('')
const captchaResetKey = ref(0)

async function loadCaptchaConfig() {
  if (siteKey.value) return
  try {
    const result = await getCaptchaConfig()
    siteKey.value = result.data?.site_key || ''
  } catch {
    errorMessage.value = '人机验证配置加载失败'
  }
}

async function submit() {
  errorMessage.value = ''
  if (captchaRequired.value && !captchaToken.value) {
    errorMessage.value = '请先完成人机验证'
    return
  }
  submitting.value = true
  try {
    await authStore.login({
      email: email.value,
      password: password.value,
      captcha_token: captchaToken.value || undefined,
    })
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/dashboard/workspaces'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '登录失败')
    if (error?.response?.data?.data?.captcha_required) {
      captchaRequired.value = true
      await loadCaptchaConfig()
    }
  } finally {
    submitting.value = false
    if (captchaToken.value) {
      captchaToken.value = ''
      captchaResetKey.value += 1
    }
  }
}
</script>

<template>
  <AuthFormShell title="登录" subtitle="继续进入你的工作台">
    <form class="auth-form" @submit.prevent="submit">
      <AuthInputField v-model.trim="email" label="邮箱" :icon="Mail" type="email" autocomplete="email" required />
      <AuthInputField v-model="password" label="密码" :icon="LockKeyhole" type="password" autocomplete="current-password" minlength="8" maxlength="72" revealable required />
      <TurnstileWidget
        v-if="captchaRequired"
        :site-key="siteKey"
        action="login"
        :reset-key="captchaResetKey"
        @verified="captchaToken = $event; errorMessage = ''"
        @expired="captchaToken = ''"
        @error="captchaToken = ''; errorMessage = '人机验证加载失败，请刷新重试'"
      />
      <p v-if="errorMessage" class="auth-error"><CircleAlert :size="14" />{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting"><span>{{ submitting ? '登录中…' : '登录' }}</span><ArrowRight :size="17" /></AppButton>
    </form>
    <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
  </AuthFormShell>
</template>
