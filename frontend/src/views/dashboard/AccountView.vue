<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
import { CalendarDays, CircleAlert, CirclePause, LockKeyhole, Mail, ShieldCheck, TrendingDown, UserPlus, UserRound, Wallet } from 'lucide-vue-next'
import { getAccount } from '../../api/account'
import AuthInputField from '../../components/auth/AuthInputField.vue'
import AppButton from '../../components/ui/AppButton.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

const authStore = useAuthStore()
const { t, n } = useI18n()
const toast = useGlobalToast()
const account = ref(null)
const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const passwordError = ref('')
const password = reactive({ current: '', next: '', confirm: '' })

async function loadAccount() {
  loading.value = true
  loadError.value = ''
  try {
    const result = await getAccount()
    if (result.code !== 0) throw new Error(result.message)
    account.value = result.data
    Object.assign(authStore.user, {
      credit_balance: result.data.credits.available,
      credit_frozen: result.data.credits.frozen,
    })
  } catch (error) {
    loadError.value = getApiErrorMessage(error, t('account.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function changePassword() {
  passwordError.value = ''
  if (password.next.length < 8 || password.next.length > 72) passwordError.value = t('account.passwordLength')
  else if (password.current === password.next) passwordError.value = t('account.passwordSame')
  else if (password.next !== password.confirm) passwordError.value = t('account.passwordMismatch')
  if (passwordError.value) return

  submitting.value = true
  try {
    await authStore.changePassword({ current_password: password.current, new_password: password.next })
    password.current = ''
    password.next = ''
    password.confirm = ''
    toast.success(t('account.passwordUpdated'))
  } catch (error) {
    passwordError.value = getApiErrorMessage(error, t('account.passwordFailed'))
  } finally {
    submitting.value = false
  }
}

function formatDate(value) {
  return formatDateTime(value, { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(loadAccount)
</script>

<template>
  <section class="account-content">
    <EmptyState v-if="loading" :title="t('account.loading')" loading />
    <EmptyState v-else-if="loadError" :title="t('account.loadFailed')" :description="loadError" tone="error">
      <AppButton variant="primary" @click="loadAccount">{{ t('common.reload') }}</AppButton>
    </EmptyState>

    <template v-else>
      <section class="account-overview-section account-summary-section">
        <header class="account-section-heading"><h1>{{ t('navigation.overview') }}</h1><p>{{ t('account.overviewDescription') }}</p></header>
        <div class="account-stats">
          <article><span><Wallet :size="18" /></span><small>{{ t('account.available') }}</small><strong>{{ n(account.credits.available) }}</strong></article>
          <article><span><CirclePause :size="18" /></span><small>{{ t('account.frozen') }}</small><strong>{{ n(account.credits.frozen) }}</strong></article>
          <article><span><TrendingDown :size="18" /></span><small>{{ t('account.consumed') }}</small><strong>{{ n(account.credits.consumed_total) }}</strong></article>
          <article><span><CalendarDays :size="18" /></span><small>{{ t('account.today') }}</small><strong>{{ n(account.credits.consumed_today) }}</strong></article>
        </div>
      </section>

      <section class="account-overview-section account-profile-section">
        <header class="account-section-heading"><h2>{{ t('account.profile') }}</h2><p>{{ t('account.profileDescription') }}</p></header>
        <dl class="account-profile">
          <div><dt><UserRound :size="16" />{{ t('auth.username') }}</dt><dd>{{ account.user.username }}</dd></div>
          <div><dt><Mail :size="16" />{{ t('auth.email') }}</dt><dd>{{ account.user.email }}</dd></div>
          <div><dt><CalendarDays :size="16" />{{ t('account.registered') }}</dt><dd>{{ formatDate(account.user.created_at) }}</dd></div>
        </dl>
      </section>

      <div class="account-detail-grid">
        <section class="account-overview-section">
          <header class="account-section-heading"><h2>{{ t('account.security') }}</h2><p>{{ t('account.securityDescription') }}</p></header>
          <form class="account-security-form" @submit.prevent="changePassword">
            <AuthInputField v-model="password.current" :label="t('account.currentPassword')" :icon="LockKeyhole" type="password" autocomplete="current-password" revealable required />
            <AuthInputField v-model="password.next" :label="t('account.newPassword')" :icon="LockKeyhole" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
            <AuthInputField v-model="password.confirm" :label="t('account.confirmPassword')" :icon="ShieldCheck" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
            <p v-if="passwordError" class="account-form-error"><CircleAlert :size="14" />{{ passwordError }}</p>
            <AppButton type="submit" variant="primary" :disabled="submitting">{{ submitting ? t('account.changingPassword') : t('account.changePassword') }}</AppButton>
          </form>
        </section>

        <section class="account-overview-section">
          <header class="account-section-heading"><h2>{{ t('account.invite') }}</h2><p>{{ t('account.inviteDescription') }}</p></header>
          <EmptyState class="account-invite" :title="t('account.inviteSoon')" :description="t('account.inviteSoonDescription')" :icon="UserPlus" />
        </section>
      </div>
    </template>
  </section>
</template>
