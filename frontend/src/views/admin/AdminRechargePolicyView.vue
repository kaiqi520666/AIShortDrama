<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getAdminBillingPolicy, updateAdminBillingPolicy } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const policy = reactive({ version: 0, reason: '', submitting: false })
const form = reactive({ rechargeMinYuan: '35', rechargeMaxYuan: '3500', unitAmountYuan: '35', unitCredits: '1000', idrRechargeMin: '150000', idrRechargeMax: '15000000', idrUnitAmount: '150000', idrUnitCredits: '1000' })

function sync(data) {
  policy.version = data.version
  policy.reason = ''
  Object.assign(form, {
    rechargeMinYuan: String(data.recharge_min_cents / 100),
    rechargeMaxYuan: String(data.recharge_max_cents / 100),
    unitAmountYuan: String(data.unit_amount_cents / 100),
    unitCredits: String(data.unit_credits),
    idrRechargeMin: String(data.idr_recharge_min),
    idrRechargeMax: String(data.idr_recharge_max),
    idrUnitAmount: String(data.idr_unit_amount),
    idrUnitCredits: String(data.idr_unit_credits),
  })
}

async function load() {
  loading.value = true
  try {
    const result = await getAdminBillingPolicy()
    if (result.code !== 0) throw new Error(result.message)
    sync(result.data)
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.rechargePolicy.loadFailed'))) }
  finally { loading.value = false }
}

async function submit() {
  const payload = {
    reason: policy.reason,
    recharge_min_cents: Number(form.rechargeMinYuan) * 100,
    recharge_max_cents: Number(form.rechargeMaxYuan) * 100,
    unit_amount_cents: Number(form.unitAmountYuan) * 100,
    unit_credits: Number(form.unitCredits),
    idr_recharge_min: Number(form.idrRechargeMin),
    idr_recharge_max: Number(form.idrRechargeMax),
    idr_unit_amount: Number(form.idrUnitAmount),
    idr_unit_credits: Number(form.idrUnitCredits),
  }
  if (!await confirmMutation({ title: t('admin.rechargePolicy.update'), message: t('admin.rechargePolicy.confirmation', {
    min: n(Number(form.rechargeMinYuan), { style: 'currency', currency: 'CNY' }),
    max: n(Number(form.rechargeMaxYuan), { style: 'currency', currency: 'CNY' }),
    amount: n(Number(form.unitAmountYuan), { style: 'currency', currency: 'CNY' }),
    credits: n(Number(form.unitCredits)),
  }) })) return
  policy.submitting = true
  try {
    const result = await updateAdminBillingPolicy(payload)
    if (result.code !== 0) throw new Error(result.message)
    sync(result.data)
    toast.success(t('admin.rechargePolicy.updated'))
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.rechargePolicy.saveFailed'))) }
  finally { policy.submitting = false }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.finance') }}</span><h1>{{ t('navigation.rechargePolicy') }}</h1><p>{{ t('admin.rechargePolicy.description') }}</p></div><b>{{ t('admin.rechargePolicy.version', { version: policy.version }) }}</b></header>
    <form class="admin-form-grid" @submit.prevent="submit">
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.minimum') }} (CNY)</span><AppInput v-model="form.rechargeMinYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.maximum') }} (CNY)</span><AppInput v-model="form.rechargeMaxYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.unitAmount') }} (CNY)</span><AppInput v-model="form.unitAmountYuan" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.unitCredits') }} (CNY)</span><AppInput v-model="form.unitCredits" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.minimum') }} (IDR)</span><AppInput v-model="form.idrRechargeMin" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.maximum') }} (IDR)</span><AppInput v-model="form.idrRechargeMax" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.unitAmount') }} (IDR)</span><AppInput v-model="form.idrUnitAmount" type="number" min="1" step="1" required /></label>
      <label class="admin-field"><span>{{ t('admin.rechargePolicy.unitCredits') }} (IDR)</span><AppInput v-model="form.idrUnitCredits" type="number" min="1" step="1" required /></label>
      <label class="admin-field admin-field--wide"><span>{{ t('common.reason') }}</span><AppInput v-model="policy.reason" maxlength="255" required :placeholder="t('common.reasonPlaceholder')" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="loading || policy.submitting || !policy.reason.trim()">{{ t(policy.submitting ? 'common.saving' : 'admin.rechargePolicy.save') }}</AppButton></div>
    </form>
  </section>
</template>
