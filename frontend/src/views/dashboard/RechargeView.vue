<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CheckCircle2, ExternalLink, RefreshCw, WalletCards } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { createRechargeOrder, getRechargeConfig, getRechargeOrder } from '../../api/recharge'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useGlobalToast()
const config = ref(null)
const amount = ref('35')
const order = ref(null)
const loading = ref(true)
const creating = ref(false)
const refreshing = ref(false)
let pollTimer
let pollStartedAt = 0

const amountCents = computed(() => Number(amount.value) * 100)
const validAmount = computed(() => Number.isInteger(Number(amount.value))
  && amountCents.value >= (config.value?.min_amount_cents ?? 3500)
  && amountCents.value <= (config.value?.max_amount_cents ?? 350000))
const activeTier = computed(() => [...(config.value?.tiers || [])]
  .reverse().find((tier) => tier.min_amount_cents <= amountCents.value))
const baseCredits = computed(() => validAmount.value ? Math.floor(amountCents.value * 1000 / 3500) : 0)
const bonusCredits = computed(() => Math.floor(baseCredits.value * (activeTier.value?.bonus_rate_bps || 0) / 10000))
const totalCredits = computed(() => baseCredits.value + bonusCredits.value)

function setAmount(cents) {
  amount.value = String(cents / 100)
}

function openPayment() {
  if (order.value?.pay_url) window.open(order.value.pay_url, '_blank', 'noopener')
}

function stopPolling() {
  clearInterval(pollTimer)
  pollTimer = undefined
}

async function refreshOrder(silent = false) {
  if (!order.value?.id && !route.query.order) return
  if (!silent) refreshing.value = true
  try {
    const result = await getRechargeOrder(order.value?.id || route.query.order)
    if (result.code !== 0) throw new Error(result.message)
    const previous = order.value?.status
    order.value = result.data
    if (result.data.credit_balance !== undefined && authStore.user) {
      authStore.user.credit_balance = result.data.credit_balance
    }
    if (result.data.status !== 'pending') stopPolling()
    if (result.data.status === 'paid' && previous !== 'paid') toast.success('积分已到账')
  } catch (error) {
    if (!silent) toast.error(error.response?.data?.message || error.message || '订单状态刷新失败')
  } finally {
    refreshing.value = false
  }
}

function startPolling() {
  stopPolling()
  pollStartedAt = Date.now()
  pollTimer = setInterval(() => {
    if (Date.now() - pollStartedAt >= 10 * 60 * 1000) return stopPolling()
    refreshOrder(true)
  }, 3000)
}

async function submit() {
  if (!validAmount.value) return
  creating.value = true
  try {
    const result = await createRechargeOrder(amountCents.value)
    if (result.code !== 0) throw new Error(result.message)
    order.value = result.data
    await router.replace({ query: { order: result.data.id } })
    startPolling()
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '支付订单创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    const result = await getRechargeConfig()
    if (result.code !== 0) throw new Error(result.message)
    config.value = result.data
    if (route.query.order) {
      await refreshOrder()
      if (order.value?.status === 'pending') startPolling()
    }
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '充值配置加载失败')
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(stopPolling)
</script>

<template>
  <section class="account-content recharge-page">
    <header class="account-section-heading"><h1>积分充值</h1><p>1000 积分 = 35 元，充值越多赠送越多</p></header>
    <EmptyState v-if="loading" loading title="正在加载充值配置" />
    <div v-else-if="config" class="recharge-layout">
      <section class="recharge-panel">
        <div class="recharge-panel__title"><div><span>选择金额</span><small>单笔支持 35–3500 元整数金额</small></div><WalletCards :size="20" /></div>
        <div class="recharge-tiers">
          <button v-for="tier in config.tiers" :key="tier.id" type="button" :class="{ active: Number(amount) === tier.min_amount_cents / 100 }" @click="setAmount(tier.min_amount_cents)">
            <strong>¥{{ tier.min_amount_cents / 100 }}</strong>
            <span>{{ tier.bonus_rate_bps ? `赠送 ${tier.bonus_rate_bps / 100}%` : '基础档' }}</span>
          </button>
        </div>
        <label class="recharge-custom"><span>自定义金额</span><div><b>¥</b><AppInput v-model="amount" type="number" min="35" max="3500" step="1" /></div></label>
        <p v-if="amount && !validAmount" class="recharge-error">请输入 35–3500 之间的整数金额</p>
        <div class="recharge-summary">
          <div><span>基础积分</span><strong>{{ baseCredits }}</strong></div>
          <div><span>赠送积分</span><strong class="is-bonus">+{{ bonusCredits }}</strong></div>
          <div><span>预计到账</span><strong>{{ totalCredits }}</strong></div>
        </div>
        <AppButton variant="primary" class="recharge-submit" :disabled="!validAmount || creating" @click="submit">{{ creating ? '正在创建订单…' : `微信支付 ¥${validAmount ? amount : 0}` }}</AppButton>
      </section>

      <section class="recharge-panel recharge-payment">
        <div class="recharge-panel__title"><div><span>微信支付</span><small>积分到账以支付平台异步通知为准</small></div></div>
        <div v-if="!order" class="recharge-payment__empty"><WalletCards :size="32" /><p>选择金额并创建支付订单</p></div>
        <div v-else-if="order.status === 'paid'" class="recharge-payment__success"><CheckCircle2 :size="48" /><h2>充值成功</h2><p>{{ order.total_credits }} 积分已到账</p><strong>当前余额 {{ order.credit_balance }}</strong></div>
        <div v-else-if="order.status === 'failed'" class="recharge-payment__failed"><h2>订单创建失败</h2><p>{{ order.error_message || '请重新创建支付订单' }}</p></div>
        <div v-else class="recharge-payment__pending">
          <img v-if="order.qr_img" :src="order.qr_img" alt="微信支付二维码" />
          <div v-else class="recharge-payment__placeholder">请打开支付页面完成付款</div>
          <h2>微信扫码支付 ¥{{ order.amount_cents / 100 }}</h2>
          <p>到账 {{ order.total_credits }} 积分，订单号 {{ order.out_trade_no }}</p>
          <div><AppButton v-if="order.pay_url" variant="primary" @click="openPayment"><ExternalLink :size="15" />打开支付页</AppButton><AppButton variant="soft" :disabled="refreshing" @click="refreshOrder()"><RefreshCw :size="15" />刷新状态</AppButton></div>
        </div>
      </section>
    </div>
  </section>
</template>
