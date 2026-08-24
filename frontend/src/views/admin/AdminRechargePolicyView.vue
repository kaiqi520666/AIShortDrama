<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getAdminBillingPolicy, updateAdminBillingPolicy } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const policy = reactive({ version: 0, reason: '', submitting: false })
const form = reactive({ rechargeMinYuan: '35', rechargeMaxYuan: '3500', unitAmountYuan: '35', unitCredits: '1000' })

function sync(data) {
  policy.version = data.version
  policy.reason = ''
  Object.assign(form, {
    rechargeMinYuan: String(data.recharge_min_cents / 100),
    rechargeMaxYuan: String(data.recharge_max_cents / 100),
    unitAmountYuan: String(data.unit_amount_cents / 100),
    unitCredits: String(data.unit_credits),
  })
}

async function load() {
  loading.value = true
  try {
    const result = await getAdminBillingPolicy()
    if (result.code !== 0) throw new Error(result.message)
    sync(result.data)
  } catch (error) { toast.error(getApiErrorMessage(error, '充值政策加载失败')) }
  finally { loading.value = false }
}

async function submit() {
  const payload = {
    reason: policy.reason,
    recharge_min_cents: Number(form.rechargeMinYuan) * 100,
    recharge_max_cents: Number(form.rechargeMaxYuan) * 100,
    unit_amount_cents: Number(form.unitAmountYuan) * 100,
    unit_credits: Number(form.unitCredits),
  }
  if (!await confirmMutation({ title: '更新充值政策', message: `起充 ¥${form.rechargeMinYuan}，封顶 ¥${form.rechargeMaxYuan}，${form.unitAmountYuan} 元兑换 ${form.unitCredits} 积分。` })) return
  policy.submitting = true
  try {
    const result = await updateAdminBillingPolicy(payload)
    if (result.code !== 0) throw new Error(result.message)
    sync(result.data)
    toast.success('充值政策已更新')
  } catch (error) { toast.error(getApiErrorMessage(error, '充值政策保存失败')) }
  finally { policy.submitting = false }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>RECHARGE POLICY</span><h1>充值政策</h1><p>管理充值金额范围与积分兑换比例</p></div><b>政策 v{{ policy.version }}</b></header>
    <form class="admin-form-grid" @submit.prevent="submit">
      <label class="admin-field"><span>起充金额（元）</span><AppInput v-model="form.rechargeMinYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>封顶金额（元）</span><AppInput v-model="form.rechargeMaxYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>兑换金额（元）</span><AppInput v-model="form.unitAmountYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>兑换积分</span><AppInput v-model="form.unitCredits" type="number" min="1" step="1" required /></label>
      <label class="admin-field admin-field--wide"><span>操作原因</span><AppInput v-model="policy.reason" maxlength="255" required placeholder="填写本次调整原因" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="loading || policy.submitting || !policy.reason.trim()">{{ policy.submitting ? '保存中…' : '保存充值政策' }}</AppButton></div>
    </form>
  </section>
</template>
