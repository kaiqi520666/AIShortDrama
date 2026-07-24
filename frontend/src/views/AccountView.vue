<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { CalendarDays, CircleAlert, CirclePause, LockKeyhole, Mail, ShieldCheck, TrendingDown, UserPlus, UserRound, Wallet } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { getAccount } from '../api/account'
import AuthInputField from '../components/auth/AuthInputField.vue'
import CreditLedgerPanel from '../components/account/CreditLedgerPanel.vue'
import AppDashboardShell from '../components/dashboard/AppDashboardShell.vue'
import AppButton from '../components/ui/AppButton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useGlobalToast } from '../composables/useGlobalUI'
import { useAuthStore } from '../stores/auth'

const sectionIds = new Set(['overview', 'credits', 'profile', 'security', 'invite'])
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useGlobalToast()
const activeSection = computed(() => {
  const section = String(route.query.section || '')
  return sectionIds.has(section) ? section : 'overview'
})
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
    loadError.value = error.response?.data?.message || error.message || '账户信息加载失败'
  } finally {
    loading.value = false
  }
}

async function signOut() {
  await authStore.logout()
  await router.replace('/')
}

async function changePassword() {
  passwordError.value = ''
  if (password.next.length < 8 || password.next.length > 72) passwordError.value = '新密码需为 8–72 位'
  else if (password.current === password.next) passwordError.value = '新密码不能与原密码相同'
  else if (password.next !== password.confirm) passwordError.value = '两次输入的新密码不一致'
  if (passwordError.value) return

  submitting.value = true
  try {
    await authStore.changePassword({ current_password: password.current, new_password: password.next })
    password.current = ''
    password.next = ''
    password.confirm = ''
    toast.success('密码已更新，其他设备已退出登录')
  } catch (error) {
    passwordError.value = error.response?.data?.message || error.message || '密码修改失败'
  } finally {
    submitting.value = false
  }
}

function formatDate(value) {
  return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(loadAccount)
</script>

<template>
  <AppDashboardShell :active-item="activeSection" :username="authStore.user?.username || '用户'" @logout="signOut">
    <section class="account-content">
        <EmptyState v-if="loading" title="正在加载账户信息" loading />
        <EmptyState v-else-if="loadError" title="账户信息加载失败" :description="loadError" tone="error">
          <AppButton variant="primary" @click="loadAccount">重新加载</AppButton>
        </EmptyState>

        <template v-else-if="activeSection === 'overview'">
          <header class="account-section-heading"><h1>账户概览</h1><p>查看当前积分使用情况</p></header>
          <div class="account-stats">
            <article><span><Wallet :size="18" /></span><small>可用积分</small><strong>{{ account.credits.available }}</strong></article>
            <article><span><CirclePause :size="18" /></span><small>冻结积分</small><strong>{{ account.credits.frozen }}</strong></article>
            <article><span><TrendingDown :size="18" /></span><small>累计消耗</small><strong>{{ account.credits.consumed_total }}</strong></article>
            <article><span><CalendarDays :size="18" /></span><small>今日消耗</small><strong>{{ account.credits.consumed_today }}</strong></article>
          </div>
          <p class="account-time-note"><CalendarDays :size="14" />今日消耗按北京时间统计</p>
        </template>

        <CreditLedgerPanel v-else-if="activeSection === 'credits'" />

        <template v-else-if="activeSection === 'profile'">
          <header class="account-section-heading"><h1>个人信息</h1><p>账户基础信息仅供查看</p></header>
          <dl class="account-profile">
            <div><dt><UserRound :size="16" />用户名</dt><dd>{{ account.user.username }}</dd></div>
            <div><dt><Mail :size="16" />邮箱</dt><dd>{{ account.user.email }}</dd></div>
            <div><dt><CalendarDays :size="16" />注册时间</dt><dd>{{ formatDate(account.user.created_at) }}</dd></div>
          </dl>
        </template>

        <template v-else-if="activeSection === 'security'">
          <header class="account-section-heading"><h1>安全设置</h1><p>修改后其他设备将立即退出登录</p></header>
          <form class="account-security-form" @submit.prevent="changePassword">
            <AuthInputField v-model="password.current" label="原密码" :icon="LockKeyhole" type="password" autocomplete="current-password" revealable required />
            <AuthInputField v-model="password.next" label="新密码" :icon="LockKeyhole" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
            <AuthInputField v-model="password.confirm" label="确认新密码" :icon="ShieldCheck" type="password" autocomplete="new-password" minlength="8" maxlength="72" revealable required />
            <p v-if="passwordError" class="account-form-error"><CircleAlert :size="14" />{{ passwordError }}</p>
            <AppButton type="submit" variant="primary" :disabled="submitting">{{ submitting ? '正在修改…' : '修改密码' }}</AppButton>
          </form>
        </template>

        <template v-else>
          <header class="account-section-heading"><h1>邀请</h1><p>邀请好友共同使用 Mooncut</p></header>
          <EmptyState class="account-invite" title="邀请功能即将开放" description="正式开放后可在此查看邀请权益" :icon="UserPlus" />
        </template>
    </section>
  </AppDashboardShell>
</template>
