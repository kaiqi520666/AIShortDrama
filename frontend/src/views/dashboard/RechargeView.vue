<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, ExternalLink, RefreshCw, WalletCards } from 'lucide-vue-next'
import QrcodeVue from 'qrcode.vue'
import { useRoute, useRouter } from 'vue-router'
import { createRechargeOrder, getRechargeConfig, getRechargeOrder, queryRechargeOrder } from '../../api/recharge'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalConfirm, useGlobalToast } from '../../composables/useGlobalUI'
import { useAuthStore } from '../../stores/auth'
import { getApiErrorMessage } from '../../utils/apiError'

const route = useRoute()
const router = useRouter()
const { t, locale, n } = useI18n()
const authStore = useAuthStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const config = ref(null)
const provider = ref('zpay')
const amount = ref('')
const order = ref(null)
const loading = ref(true)
const creating = ref(false)
const refreshing = ref(false)
let pollTimer
let pollStartedAt = 0

const providerConfig = computed(() => config.value?.payment_providers || {})
const providerOptions = computed(() => Object.entries(providerConfig.value)
  .filter(([, item]) => item.enabled)
  .map(([value]) => ({ value, label: value === 'cahaya' ? 'Cahaya QRIS' : 'ZPay / WeChat Pay' })))
const selectedProvider = computed(() => providerConfig.value[provider.value] || {})
const currency = computed(() => selectedProvider.value.currency || (provider.value === 'cahaya' ? 'IDR' : 'CNY'))
const isIdr = computed(() => currency.value === 'IDR')
const tiers = computed(() => (config.value?.tiers || []).filter((tier) => tier.currency === currency.value))
const minimum = computed(() => isIdr.value ? config.value?.idr_recharge_min : config.value?.recharge_min_cents)
const maximum = computed(() => isIdr.value ? config.value?.idr_recharge_max : config.value?.recharge_max_cents)
const unitAmount = computed(() => isIdr.value ? config.value?.idr_unit_amount : config.value?.unit_amount_cents)
const unitCredits = computed(() => isIdr.value ? config.value?.idr_unit_credits : config.value?.unit_credits)
const amountMinor = computed(() => Number(amount.value))
const validAmount = computed(() => Number.isInteger(amountMinor.value) && amountMinor.value >= minimum.value && amountMinor.value <= maximum.value)
const activeTier = computed(() => [...tiers.value].reverse().find((tier) => tier.min_amount_cents <= amountMinor.value))
const baseCredits = computed(() => validAmount.value ? Math.floor(amountMinor.value * unitCredits.value / unitAmount.value) : 0)
const bonusCredits = computed(() => Math.floor(baseCredits.value * (activeTier.value?.bonus_rate_bps || 0) / 10000))
const totalCredits = computed(() => baseCredits.value + bonusCredits.value)

function formatAmount(value, code = currency.value) {
  return n(value / (code === 'CNY' ? 100 : 1), {
    style: 'currency',
    currency: code,
    maximumFractionDigits: code === 'CNY' ? 2 : 0,
  })
}

function defaultProvider() {
  const preferred = locale.value === 'id' ? 'cahaya' : 'zpay'
  return providerConfig.value[preferred]?.enabled ? preferred : providerOptions.value[0]?.value || preferred
}

function syncAmount() {
  amount.value = String(isIdr.value ? config.value?.idr_recharge_min || 0 : config.value?.recharge_min_cents || 0)
}

function setAmount(value) {
  amount.value = String(value)
}

function openPayment() {
  if (order.value?.pay_url) window.open(order.value.pay_url, '_blank', 'noopener')
}

function stopPolling() {
  clearInterval(pollTimer)
  pollTimer = undefined
}

async function refreshOrder(silent = false, sync = false) {
  const orderId = order.value?.id || route.query.order
  if (!orderId) return
  if (!silent) refreshing.value = true
  try {
    const result = sync ? await queryRechargeOrder(orderId) : await getRechargeOrder(orderId)
    if (result.code !== 0) throw new Error(result.message)
    const previous = order.value?.status
    order.value = result.data
    if (result.data.credit_balance !== undefined && authStore.user) authStore.user.credit_balance = result.data.credit_balance
    if (result.data.status !== 'pending') stopPolling()
    if (result.data.status === 'paid' && previous !== 'paid') toast.success(t('recharge.paid'))
  } catch (error) {
    if (!silent) toast.error(getApiErrorMessage(error, t('recharge.refreshFailed')))
  } finally {
    refreshing.value = false
  }
}

function startPolling() {
  stopPolling()
  pollStartedAt = Date.now()
  pollTimer = setInterval(() => {
    if (Date.now() - pollStartedAt >= 10 * 60 * 1000) return stopPolling()
    refreshOrder(true, order.value?.provider === 'cahaya')
  }, 3000)
}

async function submit() {
  if (!validAmount.value) return
  const displayAmount = formatAmount(amountMinor.value)
  const accepted = await confirm({
    title: t('recharge.confirmTitle', { provider: provider.value === 'cahaya' ? 'Cahaya QRIS' : 'ZPay' }),
    message: t('recharge.confirmMessage', { amount: displayAmount, base: n(baseCredits.value), bonus: n(bonusCredits.value), total: n(totalCredits.value) }),
    confirmText: t('recharge.confirmPay', { amount: displayAmount }),
  })
  if (!accepted) return
  creating.value = true
  try {
    const payload = provider.value === 'cahaya'
      ? { provider: 'cahaya', amount_minor: amountMinor.value }
      : { provider: 'zpay', amount_cents: amountMinor.value }
    const result = await createRechargeOrder(payload)
    if (result.code !== 0) throw new Error(result.message)
    order.value = result.data
    await router.replace({ query: { order: result.data.id } })
    startPolling()
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('recharge.createFailed')))
  } finally {
    creating.value = false
  }
}

watch(locale, () => {
  if (!order.value && config.value) {
    provider.value = defaultProvider()
    syncAmount()
  }
})

watch(provider, () => {
  if (!order.value && config.value) syncAmount()
})

onMounted(async () => {
  try {
    const result = await getRechargeConfig()
    if (result.code !== 0) throw new Error(result.message)
    config.value = result.data
    provider.value = defaultProvider()
    syncAmount()
    if (route.query.order) {
      await refreshOrder()
      if (order.value?.status === 'pending') startPolling()
    }
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('recharge.loadFailed')))
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <section class="account-content recharge-page">
    <header class="account-section-heading"><h1>{{ t('recharge.title') }}</h1><p>{{ t('recharge.policy', { credits: unitCredits || 0, amount: formatAmount(unitAmount || 0) }) }}</p></header>
    <EmptyState v-if="loading" loading :title="t('recharge.loading')" />
    <div v-else-if="config" class="recharge-layout">
      <section class="recharge-panel">
        <div class="recharge-panel__title"><div><span>{{ t('recharge.selectProvider') }}</span><small>{{ t('recharge.providerFixedAfterOrder') }}</small></div><WalletCards :size="20" /></div>
        <AppSelect v-model="provider" :options="providerOptions" :aria-label="t('recharge.provider')" />
        <div class="recharge-panel__title recharge-panel__title--amount"><div><span>{{ t('recharge.selectAmount') }}</span><small>{{ t('recharge.amountRange', { min: formatAmount(minimum), max: formatAmount(maximum) }) }}</small></div></div>
        <div class="recharge-tiers">
          <button v-for="tier in tiers" :key="tier.id" type="button" :class="{ active: amountMinor === tier.min_amount_cents }" @click="setAmount(tier.min_amount_cents)">
            <strong>{{ formatAmount(tier.min_amount_cents) }}</strong>
            <span>{{ tier.bonus_rate_bps ? t('recharge.bonus', { rate: tier.bonus_rate_bps / 100 }) : t('recharge.baseTier') }}</span>
          </button>
        </div>
        <label class="recharge-custom"><span>{{ t('recharge.customAmount') }}</span><div><b>{{ currency }}</b><AppInput v-model="amount" type="number" :min="minimum" :max="maximum" step="1" /></div></label>
        <p v-if="amount && !validAmount" class="recharge-error">{{ t('recharge.invalidAmount', { min: formatAmount(minimum), max: formatAmount(maximum) }) }}</p>
        <div class="recharge-summary"><div><span>{{ t('recharge.baseCredits') }}</span><strong>{{ n(baseCredits) }}</strong></div><div><span>{{ t('recharge.bonusCredits') }}</span><strong class="is-bonus">+{{ n(bonusCredits) }}</strong></div><div><span>{{ t('recharge.totalCredits') }}</span><strong>{{ n(totalCredits) }}</strong></div></div>
        <AppButton variant="primary" class="recharge-submit" :disabled="!validAmount || creating" @click="submit">{{ creating ? t('recharge.creating') : t('recharge.pay', { provider: provider === 'cahaya' ? 'Cahaya QRIS' : 'ZPay', amount: validAmount ? formatAmount(amountMinor) : formatAmount(0) }) }}</AppButton>
      </section>

      <section class="recharge-panel recharge-payment">
        <div class="recharge-panel__title"><div><span>{{ order ? (order.provider === 'cahaya' ? 'Cahaya QRIS' : 'ZPay / WeChat Pay') : t('recharge.payment') }}</span><small>{{ t('recharge.asyncNotice') }}</small></div></div>
        <div v-if="!order" class="recharge-payment__empty"><WalletCards :size="32" /><p>{{ t('recharge.empty') }}</p></div>
        <div v-else-if="order.status === 'paid'" class="recharge-payment__success"><CheckCircle2 :size="48" /><h2>{{ t('recharge.success') }}</h2><p>{{ t('recharge.arrived', { credits: n(order.total_credits) }) }}</p><strong>{{ t('recharge.balance', { balance: n(order.credit_balance || 0) }) }}</strong></div>
        <div v-else-if="order.status === 'failed'" class="recharge-payment__failed"><h2>{{ t('recharge.failed') }}</h2><p>{{ t('errors.payment_unavailable') }}</p></div>
        <div v-else class="recharge-payment__pending">
          <QrcodeVue v-if="order.provider === 'cahaya' && order.qr_code" :value="order.qr_code" :size="210" level="M" class="recharge-qr" />
          <img v-else-if="order.qr_img" :src="order.qr_img" :alt="t('recharge.qrAlt')" />
          <div v-else class="recharge-payment__placeholder">{{ t('recharge.openPaymentHint') }}</div>
          <h2>{{ t('recharge.scanPay', { provider: order.provider === 'cahaya' ? 'QRIS' : 'WeChat Pay', amount: formatAmount(order.amount_minor || order.amount_cents, order.currency) }) }}</h2>
          <p>{{ t('recharge.orderInfo', { credits: n(order.total_credits), order: order.out_trade_no }) }}</p>
          <div><AppButton v-if="order.pay_url" variant="primary" @click="openPayment"><ExternalLink :size="15" />{{ t('recharge.openPayment') }}</AppButton><AppButton variant="soft" :disabled="refreshing" @click="refreshOrder(false, order.provider === 'cahaya')"><RefreshCw :size="15" />{{ t('recharge.refresh') }}</AppButton></div>
        </div>
      </section>
    </div>
  </section>
</template>
