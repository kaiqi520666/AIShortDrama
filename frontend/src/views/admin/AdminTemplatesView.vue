<script setup>
import { onMounted, ref, watch } from 'vue'
import { Check, RefreshCw } from 'lucide-vue-next'
import { getAdminContentTemplate, updateAdminContentTemplate } from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppTabs from '../../components/ui/AppTabs.vue'
import AppTextarea from '../../components/ui/AppTextarea.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const currentKey = ref('product_visual')
const form = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const reason = ref('')
const templateOptions = [
  { value: 'product_visual', label: '商品图种' },
  { value: 'product_storyboard', label: '商品分镜' },
]
const durationOptions = [15, 30, 45, 60]

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getAdminContentTemplate(currentKey.value)
    if (result.code !== 0) throw new Error(result.message)
    form.value = clone(result.data)
    reason.value = ''
  } catch (requestError) {
    error.value = getApiErrorMessage(requestError, '内容模板加载失败')
    toast.error(error.value)
  } finally {
    loading.value = false
  }
}

function toggleDuration(duration, checked) {
  const durations = form.value.config.durations
  form.value.config.durations = checked
    ? [...new Set([...durations, duration])].sort((a, b) => a - b)
    : durations.filter((item) => item !== duration)
}

async function save() {
  const payload = { enabled: form.value.enabled, config: form.value.config, reason: reason.value }
  if (!await confirmMutation({
    title: '更新内容模板',
    message: `${currentKey.value === 'product_visual' ? '商品图种' : '商品分镜'}模板将升级到下一版本，并仅用于后续新节点与新生成。`,
  })) return
  saving.value = true
  try {
    const result = await updateAdminContentTemplate(currentKey.value, payload)
    if (result.code !== 0) throw new Error(result.message)
    form.value = clone(result.data)
    reason.value = ''
    toast.success('内容模板已更新')
  } catch (requestError) {
    toast.error(getApiErrorMessage(requestError, '内容模板保存失败'))
  } finally {
    saving.value = false
  }
}

watch(currentKey, load)
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>CONTENT TEMPLATE</span><h1>内容模板</h1><p>调整商品图种和 UGC 分镜的业务文案、默认选项与启用状态</p></div><b v-if="form">版本 v{{ form.version }}</b></header>
    <AppTabs v-model="currentKey" :options="templateOptions" aria-label="内容模板类型" />
    <EmptyState v-if="error" tone="error" title="内容模板加载失败" :description="error"><AppButton variant="primary" @click="load">重新加载</AppButton></EmptyState>
    <EmptyState v-else-if="loading || !form" loading title="正在加载内容模板" />
    <form v-else class="admin-template-form" @submit.prevent="save">
      <div class="admin-template-form__top">
        <label class="admin-check"><input v-model="form.enabled" type="checkbox" /><span>模板启用</span></label>
        <small>保存后只影响后续新节点和新生成，已有画布不会被覆盖。</small>
      </div>

      <template v-if="currentKey === 'product_visual'">
        <section v-for="group in form.config.groups" :key="group.id" class="admin-template-block">
          <header><AppInput v-model="group.label" maxlength="64" :aria-label="`${group.id} 分组名称`" /><small>{{ group.id }}</small></header>
          <div class="admin-template-items">
            <label v-for="item in group.items" :key="item.id" class="admin-template-item">
              <AppInput v-model="item.label" maxlength="64" :aria-label="`${item.id} 图种名称`" />
              <span>{{ item.id }}</span>
              <span class="admin-check"><input v-model="item.default_enabled" type="checkbox" /><i><Check :size="13" /></i>默认启用</span>
            </label>
          </div>
        </section>
        <label class="admin-field"><span>业务指令块</span><AppTextarea v-model="form.config.business_instruction" rows="6" maxlength="6000" placeholder="可选：补充商品图种的业务要求" /></label>
      </template>

      <template v-else>
        <section class="admin-template-block">
          <header><strong>固定 UGC 分镜模板</strong><small>{{ form.config.templates[0].id }}</small></header>
          <div class="admin-form-grid"><label class="admin-field"><span>模板名称</span><AppInput v-model="form.config.templates[0].label" maxlength="64" /></label><label class="admin-field"><span>模板描述</span><AppInput v-model="form.config.templates[0].description" maxlength="255" /></label></div>
          <label class="admin-check"><input v-model="form.config.templates[0].enabled" type="checkbox" /><span>模板启用</span></label>
        </section>
        <section class="admin-template-block"><header><strong>允许总时长</strong><small>固定以 15 秒为分段单位</small></header><div class="admin-duration-options"><label v-for="duration in durationOptions" :key="duration" class="admin-check"><input type="checkbox" :checked="form.config.durations.includes(duration)" @change="toggleDuration(duration, $event.target.checked)" /><span>{{ duration }} 秒</span></label></div></section>
        <label class="admin-field"><span>业务指令块</span><AppTextarea v-model="form.config.business_instruction" rows="8" maxlength="6000" required /></label>
      </template>

      <label class="admin-field"><span>操作原因</span><AppInput v-model="reason" maxlength="255" required placeholder="填写本次调整原因" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="saving || !reason.trim()">{{ saving ? '保存中…' : '保存内容模板' }}</AppButton><AppButton type="button" variant="soft" :disabled="saving" @click="load"><RefreshCw :size="15" />恢复已保存版本</AppButton></div>
    </form>
  </section>
</template>
