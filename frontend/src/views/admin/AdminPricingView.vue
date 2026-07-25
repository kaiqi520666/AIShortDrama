<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Pencil } from 'lucide-vue-next'
import { getAdminPricing, updateAdminPricing } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const loading = ref(false)
const items = ref([])
const dialog = reactive({ rule: null, reason: '', submitting: false, form: {} })
const mediaOptions = ['text', 'image', 'video', 'audio'].map((value) => ({ value, label: ({ text: '文本', image: '图片', video: '视频', audio: '音频' })[value] }))
const enabledOptions = [{ value: 'true', label: '启用' }, { value: 'false', label: '停用' }]
async function load() { loading.value = true; try { const result = await getAdminPricing(); if (result.code !== 0) throw new Error(result.message); items.value = result.data } catch (error) { toast.error(error.response?.data?.message || error.message) } finally { loading.value = false } }
function open(rule) { dialog.rule = rule; dialog.reason = ''; dialog.form = { ...rule, enabled: String(rule.enabled) } }
function numberOrNull(value) { return value === '' || value === null ? null : Number(value) }
async function submit() {
  dialog.submitting = true
  try {
    const form = dialog.form
    const payload = { reason: dialog.reason, provider: form.provider, media_type: form.media_type, model: form.model, specification: form.specification, billing_unit: form.billing_unit, cost_per_unit: numberOrNull(form.cost_per_unit), input_cost_per_million: numberOrNull(form.input_cost_per_million), output_cost_per_million: numberOrNull(form.output_cost_per_million), base_credits: numberOrNull(form.base_credits), freeze_credits: numberOrNull(form.freeze_credits), multiplier: Number(form.multiplier), enabled: form.enabled === 'true' }
    const result = await updateAdminPricing(dialog.rule.id, payload); if (result.code !== 0) throw new Error(result.message)
    dialog.rule = null; toast.success('计费规则已更新'); await load()
  } catch (error) { toast.error(error.response?.data?.message || error.message || '保存失败') } finally { dialog.submitting = false }
}
onMounted(load)
</script>

<template><section class="admin-page"><header class="admin-page__header"><div><span>PRICING CONTROL</span><h1>模型计费</h1><p>修改后仅影响新创建的生成任务</p></div><b>{{ items.length }} 条规则</b></header><EmptyState v-if="loading" title="正在加载计费规则" loading /><div v-else class="admin-table-wrap"><table class="admin-table"><thead><tr><th>模型</th><th>类型 / 规格</th><th>成本价</th><th>基础 / 冻结积分</th><th>倍率</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="rule in items" :key="rule.id"><td><strong>{{ rule.model }}</strong><small>{{ rule.provider }}</small></td><td>{{ rule.media_type }} · {{ rule.specification || '默认' }}</td><td>{{ rule.cost_per_unit ?? '—' }}</td><td>{{ rule.base_credits ?? '—' }} / {{ rule.freeze_credits ?? '—' }}</td><td>× {{ rule.multiplier }}</td><td><span class="admin-status" :class="rule.enabled ? 'is-active' : 'is-disabled'">{{ rule.enabled ? '启用' : '停用' }}</span></td><td><AppButton size="sm" variant="soft" @click="open(rule)"><Pencil :size="14" />编辑</AppButton></td></tr></tbody></table></div><AdminDialog v-if="dialog.rule" v-model:reason="dialog.reason" title="编辑计费规则" :description="dialog.rule.model" :submitting="dialog.submitting" @close="dialog.rule = null" @submit="submit"><div class="admin-form-grid"><label class="admin-field"><span>供应商</span><AppInput v-model="dialog.form.provider" required /></label><label class="admin-field"><span>模型</span><AppInput v-model="dialog.form.model" required /></label><label class="admin-field"><span>媒体类型</span><AppSelect v-model="dialog.form.media_type" :options="mediaOptions" aria-label="媒体类型" /></label><label class="admin-field"><span>规格</span><AppInput v-model="dialog.form.specification" /></label><label class="admin-field"><span>计费单位</span><AppInput v-model="dialog.form.billing_unit" required /></label><label class="admin-field"><span>成本价</span><AppInput v-model="dialog.form.cost_per_unit" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>输入/百万 Token</span><AppInput v-model="dialog.form.input_cost_per_million" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>输出/百万 Token</span><AppInput v-model="dialog.form.output_cost_per_million" type="number" min="0" step="0.000001" /></label><label class="admin-field"><span>基础积分</span><AppInput v-model="dialog.form.base_credits" type="number" min="0" /></label><label class="admin-field"><span>冻结积分</span><AppInput v-model="dialog.form.freeze_credits" type="number" min="0" /></label><label class="admin-field"><span>倍率</span><AppInput v-model="dialog.form.multiplier" type="number" min="0.001" max="100" step="0.001" required /></label><label class="admin-field"><span>状态</span><AppSelect v-model="dialog.form.enabled" :options="enabledOptions" aria-label="启用状态" /></label></div></AdminDialog></section></template>
