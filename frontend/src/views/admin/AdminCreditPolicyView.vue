<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getAdminCreditPolicy, updateAdminCreditPolicy } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const policy = reactive({ version: 0, reason: '', submitting: false })
const form = reactive({
  registration_bonus_enabled: true,
  registration_bonus_credits: '10',
  daily_refill_enabled: true,
  daily_minimum_credits: '10',
})

async function load() {
  loading.value = true
  try {
    const result = await getAdminCreditPolicy()
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(policy, { version: result.data.version, reason: '' })
    Object.assign(form, {
      registration_bonus_enabled: result.data.registration_bonus_enabled,
      registration_bonus_credits: String(result.data.registration_bonus_credits),
      daily_refill_enabled: result.data.daily_refill_enabled,
      daily_minimum_credits: String(result.data.daily_minimum_credits),
    })
  } catch (error) { toast.error(getApiErrorMessage(error, '积分策略加载失败')) }
  finally { loading.value = false }
}

async function submit() {
  const payload = {
    reason: policy.reason,
    registration_bonus_enabled: form.registration_bonus_enabled,
    registration_bonus_credits: Number(form.registration_bonus_credits),
    daily_refill_enabled: form.daily_refill_enabled,
    daily_minimum_credits: Number(form.daily_minimum_credits),
  }
  if (!await confirmMutation({ title: '更新积分策略', message: `注册赠送 ${payload.registration_bonus_credits} 积分，每日最低 ${payload.daily_minimum_credits} 积分。` })) return
  policy.submitting = true
  try {
    const result = await updateAdminCreditPolicy(payload)
    if (result.code !== 0) throw new Error(result.message)
    policy.version = result.data.version
    policy.reason = ''
    toast.success('积分策略已更新')
  } catch (error) { toast.error(getApiErrorMessage(error, '积分策略保存失败')) }
  finally { policy.submitting = false }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>CREDIT POLICY</span><h1>积分策略</h1><p>管理注册赠送与每日最低可用积分</p></div><b>策略 v{{ policy.version }}</b></header>
    <form class="admin-policy-form" @submit.prevent="submit">
      <fieldset class="admin-policy-group" :disabled="loading">
        <legend>注册赠送</legend>
        <label class="admin-check"><input v-model="form.registration_bonus_enabled" type="checkbox" /><span>启用新用户注册赠送</span></label>
        <label class="admin-field"><span>赠送积分</span><AppInput v-model="form.registration_bonus_credits" type="number" min="1" max="1000000" step="1" required /></label>
      </fieldset>
      <fieldset class="admin-policy-group" :disabled="loading">
        <legend>每日补足</legend>
        <label class="admin-check"><input v-model="form.daily_refill_enabled" type="checkbox" /><span>启用每日最低积分补足</span></label>
        <label class="admin-field"><span>最低可用积分</span><AppInput v-model="form.daily_minimum_credits" type="number" min="1" max="1000000" step="1" required /></label>
      </fieldset>
      <label class="admin-field"><span>操作原因</span><AppInput v-model="policy.reason" maxlength="255" required placeholder="填写本次调整原因" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="loading || policy.submitting || !policy.reason.trim()">{{ policy.submitting ? '保存中…' : '保存积分策略' }}</AppButton></div>
    </form>
  </section>
</template>
