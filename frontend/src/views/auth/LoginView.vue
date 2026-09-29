<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()
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
    errorMessage.value = t('auth.captchaConfigFailed')
  }
}

async function submit() {
  errorMessage.value = ''
  if (captchaRequired.value && !captchaToken.value) {
    errorMessage.value = t('auth.captchaRequired')
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
    errorMessage.value = getApiErrorMessage(error, t('auth.loginFailed'))
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
  <AuthFormShell :title="t('auth.login')" :subtitle="t('auth.loginSubtitle')">
    <form class="auth-form" @submit.prevent="submit">
      <AuthInputField v-model.trim="email" :label="t('auth.email')" :icon="Mail" type="email" autocomplete="email" required />
      <AuthInputField v-model="password" :label="t('auth.password')" :icon="LockKeyhole" type="password" autocomplete="current-password" minlength="8" maxlength="72" revealable required />
      <TurnstileWidget
        v-if="captchaRequired"
        :site-key="siteKey"
        action="login"
        :reset-key="captchaResetKey"
        @verified="captchaToken = $event; errorMessage = ''"
        @expired="captchaToken = ''"
        @error="captchaToken = ''; errorMessage = t('auth.captchaFailed')"
      />
      <p v-if="errorMessage" class="auth-error"><CircleAlert :size="14" />{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting"><span>{{ submitting ? t('auth.loggingIn') : t('auth.login') }}</span><ArrowRight :size="17" /></AppButton>
    </form>
    <p class="auth-switch">{{ t('auth.noAccount') }} <RouterLink to="/register">{{ t('auth.register') }}</RouterLink></p>
  </AuthFormShell>
</template>
