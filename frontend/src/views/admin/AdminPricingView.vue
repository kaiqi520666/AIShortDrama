<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil } from 'lucide-vue-next'
import { getAdminPricing, updateAdminPricing } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const items = ref([])
const dialog = reactive({ rule: null, reason: '', submitting: false, form: {} })
const enabledOptions = computed(() => [{ value: 'true', label: t('admin.enabled') }, { value: 'false', label: t('admin.disabled') }])
const columns = computed(() => [
  { key: 'model', label: t('admin.model') },
  { key: 'specification', label: t('admin.pricing.specification') },
  { key: 'cost_per_unit', label: t('admin.pricing.cost') },
  { key: 'credits', label: t('admin.pricing.credits') },
  { key: 'multiplier', label: t('admin.pricing.multiplier') },
  { key: 'enabled', label: t('admin.status') },
  { key: 'actions', label: t('admin.actions') },
])
async function load() { loading.value = true; try { const result = await getAdminPricing(); if (result.code !== 0) throw new Error(result.message); items.value = result.data } catch (error) { toast.error(getApiErrorMessage(error, t('admin.pricing.loadFailed'))) } finally { loading.value = false } }
function open(rule) { dialog.rule = rule; dialog.reason = ''; dialog.form = { ...rule, enabled: String(rule.enabled) } }
function numberOrNull(value) { return value === '' || value === null ? null : Number(value) }
async function submit() {
  dialog.submitting = true
  try {
    const form = dialog.form
    const payload = { reason: dialog.reason, cost_per_unit: numberOrNull(form.cost_per_unit), input_cost_per_million: numberOrNull(form.input_cost_per_million), output_cost_per_million: numberOrNull(form.output_cost_per_million), base_credits: numberOrNull(form.base_credits), freeze_credits: numberOrNull(form.freeze_credits), multiplier: Number(form.multiplier), enabled: form.enabled === 'true' }
    if (!await confirmMutation({ title: t('admin.pricing.update'), message: `${dialog.rule.model} · ${dialog.rule.specification || t('admin.pricing.defaultSpecification')}` })) return
    const result = await updateAdminPricing(dialog.rule.id, payload); if (result.code !== 0) throw new Error(result.message)
    dialog.rule = null; toast.success(t('admin.pricing.updated')); await load()
  } catch (error) { toast.error(getApiErrorMessage(error, t('common.saveFailed'))) } finally { dialog.submitting = false }
}
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.finance') }}</span><h1>{{ t('navigation.modelPricing') }}</h1><p>{{ t('admin.pricing.description') }}</p></div><b>{{ t('admin.pricing.count', { count: n(items.length) }) }}</b></header>
    <AppDataTable :columns="columns" :items="items" :loading="loading" :loading-title="t('admin.pricing.loading')" :empty-title="t('admin.pricing.empty')" min-width="900px">
      <template #cell-model="{ item: rule }"><strong>{{ rule.model }}</strong><small>{{ rule.provider }}</small></template>
      <template #cell-specification="{ item: rule }">{{ t(`home.${rule.media_type}`) }} · {{ rule.specification || t('admin.default') }}</template>
      <template #cell-cost_per_unit="{ value }">{{ value == null ? '—' : n(Number(value), { maximumFractionDigits: 6 }) }}</template>
      <template #cell-credits="{ item: rule }">{{ rule.base_credits == null ? '—' : n(rule.base_credits) }} / {{ rule.freeze_credits == null ? '—' : n(rule.freeze_credits) }}</template>
      <template #cell-multiplier="{ value }">× {{ n(Number(value), { maximumFractionDigits: 3 }) }}</template>
      <template #cell-enabled="{ item: rule }"><span class="admin-status" :class="rule.enabled ? 'is-active' : 'is-disabled'">{{ t(rule.enabled ? 'admin.enabled' : 'admin.disabled') }}</span></template>
      <template #cell-actions="{ item: rule }"><AppButton size="sm" variant="soft" @click="open(rule)"><Pencil :size="14" />{{ t('common.edit') }}</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="dialog.rule" v-model:reason="dialog.reason" :title="t('admin.pricing.edit')" :description="`${dialog.rule.model} · ${dialog.rule.media_type} · ${dialog.rule.specification || t('admin.pricing.defaultSpecification')}`" :submitting="dialog.submitting" @close="dialog.rule = null" @submit="submit"><div class="admin-form-grid"><label class="admin-field"><span>{{ t('admin.pricing.cost') }}</span><AppInput v-model="dialog.form.cost_per_unit" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>{{ t('admin.pricing.inputCost') }}</span><AppInput v-model="dialog.form.input_cost_per_million" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>{{ t('admin.pricing.outputCost') }}</span><AppInput v-model="dialog.form.output_cost_per_million" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>{{ t('admin.pricing.baseCredits') }}</span><AppInput v-model="dialog.form.base_credits" type="number" min="0" /></label><label class="admin-field"><span>{{ t('account.frozen') }}</span><AppInput v-model="dialog.form.freeze_credits" type="number" min="0" /></label><label class="admin-field"><span>{{ t('admin.pricing.multiplier') }}</span><AppInput v-model="dialog.form.multiplier" type="number" min="0.001" max="100" step="0.001" required /></label><label class="admin-field"><span>{{ t('admin.status') }}</span><AppSelect v-model="dialog.form.enabled" :options="enabledOptions" :aria-label="t('admin.models.enabledStatus')" /></label></div></AdminDialog>
  </section>
</template>
