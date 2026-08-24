<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, CircleAlert, KeyRound, LockKeyhole, Mail, UserRound } from 'lucide-vue-next'
import AuthFormShell from '../../components/auth/AuthFormShell.vue'
import AuthInputField from '../../components/auth/AuthInputField.vue'
import TurnstileWidget from '../../components/auth/TurnstileWidget.vue'
import AppButton from '../../components/ui/AppButton.vue'
import { getCaptchaConfig, sendRegistrationEmailCode } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const email = ref('')
const password = ref('')
const verificationCode = ref('')
const errorMessage = ref('')
const submitting = ref(false)
const codeSubmitting = ref(false)
const cooldown = ref(0)
const siteKey = ref('')
const captchaToken = ref('')
const captchaResetKey = ref(0)
let cooldownTimer

onMounted(async () => {
  try {
    const result = await getCaptchaConfig()
    siteKey.value = result.data?.site_key || ''
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '人机验证配置加载失败')
  }
})

onBeforeUnmount(() => window.clearInterval(cooldownTimer))

async function sendCode() {
  errorMessage.value = ''
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    errorMessage.value = '请先输入有效邮箱'
    return
  }
  if (!captchaToken.value || codeSubmitting.value || cooldown.value) {
    if (!captchaToken.value) errorMessage.value = '请先完成人机验证'
    return
  }
  codeSubmitting.value = true
  try {
    const result = await sendRegistrationEmailCode({
      email: email.value,
      captcha_token: captchaToken.value,
    })
    cooldown.value = result.data?.cooldown_seconds || 60
    cooldownTimer = window.setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) window.clearInterval(cooldownTimer)
    }, 1000)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '验证码发送失败')
  } finally {
    codeSubmitting.value = false
    captchaToken.value = ''
    captchaResetKey.value += 1
  }
}

async function submit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await authStore.register({
      username: username.value,
      email: email.value,
      password: password.value,
      verification_code: verificationCode.value,
    })
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
      <AuthInputField v-model.trim="verificationCode" label="验证码" :icon="KeyRound" inputmode="numeric" autocomplete="one-time-code" minlength="6" maxlength="6" pattern="[0-9]{6}" required>
        <template #action>
          <AppButton class="auth-code-button" type="button" variant="soft" size="sm" :disabled="codeSubmitting || cooldown > 0" @click="sendCode">
            {{ cooldown > 0 ? `${cooldown}s 后重发` : codeSubmitting ? '发送中…' : '发送验证码' }}
          </AppButton>
        </template>
      </AuthInputField>
      <AuthInputField v-model="password" label="密码" :icon="LockKeyhole" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
      <TurnstileWidget
        v-if="cooldown === 0"
        :site-key="siteKey"
        action="register_email"
        :reset-key="captchaResetKey"
        @verified="captchaToken = $event; errorMessage = ''"
        @expired="captchaToken = ''"
        @error="captchaToken = ''; errorMessage = '人机验证加载失败，请刷新重试'"
      />
      <p v-if="errorMessage" class="auth-error"><CircleAlert :size="14" />{{ errorMessage }}</p>
      <AppButton type="submit" variant="primary" size="lg" block :disabled="submitting"><span>{{ submitting ? '注册中…' : '注册并登录' }}</span><ArrowRight :size="17" /></AppButton>
    </form>
    <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
  </AuthFormShell>
</template>
