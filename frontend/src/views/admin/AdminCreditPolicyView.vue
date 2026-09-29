<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getAdminCreditPolicy, updateAdminCreditPolicy } from '../../api/admin'
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
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.creditPolicy.loadFailed'))) }
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
  if (!await confirmMutation({ title: t('admin.creditPolicy.update'), message: t('admin.creditPolicy.confirmation', { bonus: n(payload.registration_bonus_credits), minimum: n(payload.daily_minimum_credits) }) })) return
  policy.submitting = true
  try {
    const result = await updateAdminCreditPolicy(payload)
    if (result.code !== 0) throw new Error(result.message)
    policy.version = result.data.version
    policy.reason = ''
    toast.success(t('admin.creditPolicy.updated'))
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.creditPolicy.saveFailed'))) }
  finally { policy.submitting = false }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.finance') }}</span><h1>{{ t('navigation.creditPolicy') }}</h1><p>{{ t('admin.creditPolicy.description') }}</p></div><b>{{ t('admin.creditPolicy.version', { version: policy.version }) }}</b></header>
    <form class="admin-policy-form" @submit.prevent="submit">
      <fieldset class="admin-policy-group" :disabled="loading">
        <legend>{{ t('admin.creditPolicy.registration') }}</legend>
        <label class="admin-check"><input v-model="form.registration_bonus_enabled" type="checkbox" /><span>{{ t('admin.creditPolicy.enableRegistration') }}</span></label>
        <label class="admin-field"><span>{{ t('admin.creditPolicy.bonus') }}</span><AppInput v-model="form.registration_bonus_credits" type="number" min="1" max="1000000" step="1" required /></label>
      </fieldset>
      <fieldset class="admin-policy-group" :disabled="loading">
        <legend>{{ t('admin.creditPolicy.daily') }}</legend>
        <label class="admin-check"><input v-model="form.daily_refill_enabled" type="checkbox" /><span>{{ t('admin.creditPolicy.enableDaily') }}</span></label>
        <label class="admin-field"><span>{{ t('admin.creditPolicy.minimum') }}</span><AppInput v-model="form.daily_minimum_credits" type="number" min="1" max="1000000" step="1" required /></label>
      </fieldset>
      <label class="admin-field"><span>{{ t('common.reason') }}</span><AppInput v-model="policy.reason" maxlength="255" required :placeholder="t('common.reasonPlaceholder')" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="loading || policy.submitting || !policy.reason.trim()">{{ t(policy.submitting ? 'common.saving' : 'admin.creditPolicy.save') }}</AppButton></div>
    </form>
  </section>
</template>
