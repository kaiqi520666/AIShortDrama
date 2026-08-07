<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Check, CircleAlert, RefreshCw } from 'lucide-vue-next'
import {
  getAdminContentTemplate,
  getAdminContentTemplates,
  updateAdminContentTemplate,
} from '../../api/admin'
import AppButton from '../../components/ui/AppButton.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppTabs from '../../components/ui/AppTabs.vue'
import AppTextarea from '../../components/ui/AppTextarea.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const durationOptions = [15, 30, 45, 60]
const promptFields = {
  product_storyboard: [
    ['director_role', '导演角色', ''],
    ['shooting_style', '拍摄风格', ''],
    ['dialogue_no_character', '无角色对白规则', ''],
    ['dialogue_with_characters', '有角色对白规则', '{character_count} {speaker_examples}'],
    ['image_rules', '生图规则', '{columns} {rows} {ratio}'],
    ['video_rules', '视频规则', '{ratio}'],
    ['first_segment_rule', '第一段规则', '{segment}'],
    ['extend_segment_rule', '后续延续规则', '{segment} {previous_segment}'],
  ],
  commerce_drama: [
    ['creative_direction', '创作方向', ''],
    ['story_structure', '剧情结构', ''],
    ['character_rules', '角色规则', ''],
    ['dialogue_rules', '对白规则', ''],
    ['product_placement_rules', '商品植入规则', ''],
    ['image_rules', '生图规则', ''],
    ['video_rules', '视频规则', ''],
    ['continuity_rules', '连续性规则', ''],
    ['forbidden_rules', '禁止项', ''],
  ],
}

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const catalog = ref([])
const currentKey = ref('product_visual')
const form = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const reason = ref('')

const groups = computed(() => {
  const result = []
  for (const item of catalog.value) {
    let group = result.find((entry) => entry.id === item.group)
    if (!group) {
      group = { id: item.group, label: item.group_label, options: [] }
      result.push(group)
    }
    group.options.push({ value: item.key, label: item.label })
  }
  return result
})
const currentCatalogItem = computed(() => catalog.value.find((item) => item.key === currentKey.value))
const isUgc = computed(() => currentKey.value === 'product_storyboard')
const isDrama = computed(() => currentKey.value === 'commerce_drama')
const currentPromptFields = computed(() => promptFields[currentKey.value] || [])

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

async function loadCatalog() {
  const result = await getAdminContentTemplates()
  if (result.code !== 0) throw new Error(result.message)
  catalog.value = result.data
  if (!catalog.value.some((item) => item.key === currentKey.value)) {
    currentKey.value = catalog.value[0]?.key || ''
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (!catalog.value.length) await loadCatalog()
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

async function reloadAll() {
  catalog.value = []
  await load()
}

function toggleDuration(duration, checked) {
  const durations = form.value.config.durations
  form.value.config.durations = checked
    ? [...new Set([...durations, duration])].sort((a, b) => a - b)
    : durations.filter((item) => item !== duration)
}

async function save() {
  const item = currentCatalogItem.value
  const payload = { enabled: isDrama.value ? false : form.value.enabled, config: form.value.config, reason: reason.value }
  if (!await confirmMutation({
    title: '更新内容模板',
    message: `${item?.label || currentKey.value}将升级到下一版本，并仅用于后续新节点与新生成。`,
  })) return
  saving.value = true
  try {
    const result = await updateAdminContentTemplate(currentKey.value, payload)
    if (result.code !== 0) throw new Error(result.message)
    form.value = clone(result.data)
    const index = catalog.value.findIndex((entry) => entry.key === currentKey.value)
    if (index >= 0) catalog.value[index] = { ...catalog.value[index], ...clone(result.data) }
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
    <header class="admin-page__header">
      <div><span>CONTENT TEMPLATE</span><h1>内容模板</h1><p>管理商品图片模板和内容创作模板，配置仅影响后续生成。</p></div>
      <b v-if="form">版本 v{{ form.version }}</b>
    </header>

    <nav v-if="catalog.length" class="admin-template-nav" aria-label="内容模板分类">
      <section v-for="group in groups" :key="group.id">
        <span>{{ group.label }}</span>
        <AppTabs v-model="currentKey" :options="group.options" :aria-label="group.label" />
      </section>
    </nav>

    <EmptyState v-if="error" tone="error" title="内容模板加载失败" :description="error"><AppButton variant="primary" @click="reloadAll">重新加载</AppButton></EmptyState>
    <EmptyState v-else-if="loading || !form" loading title="正在加载内容模板" />
    <form v-else class="admin-template-form" @submit.prevent="save">
      <div class="admin-template-form__top">
        <label class="admin-check" :class="{ 'is-disabled': isDrama }"><input v-model="form.enabled" type="checkbox" :disabled="isDrama" /><span>模板启用</span></label>
        <small>保存后只影响后续新节点和新生成，已有画布不会被覆盖。</small>
      </div>

      <div v-if="isDrama" class="admin-template-notice" role="status"><CircleAlert :size="17" /><div><strong>流程待接入</strong><span>当前仅允许维护草稿区块，生成器接入前不能启用。</span></div></div>

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
          <header><strong>{{ isUgc ? 'UGC 种草基础信息' : '短剧带货草稿' }}</strong><small>{{ isUgc ? form.config.templates[0].id : 'commerce_drama' }}</small></header>
          <div v-if="isUgc" class="admin-form-grid">
            <label class="admin-field"><span>模板名称</span><AppInput v-model="form.config.templates[0].label" maxlength="64" /></label>
            <label class="admin-field"><span>模板描述</span><AppInput v-model="form.config.templates[0].description" maxlength="255" /></label>
          </div>
          <div v-else class="admin-form-grid">
            <label class="admin-field"><span>模板名称</span><AppInput v-model="form.config.label" maxlength="64" /></label>
            <label class="admin-field"><span>模板描述</span><AppInput v-model="form.config.description" maxlength="255" /></label>
          </div>
          <label v-if="isUgc" class="admin-check"><input v-model="form.config.templates[0].enabled" type="checkbox" /><span>UGC 选项可用</span></label>
        </section>

        <section class="admin-template-block">
          <header><strong>允许总时长</strong><small>UGC 固定以 15 秒为分段单位</small></header>
          <div class="admin-duration-options"><label v-for="duration in durationOptions" :key="duration" class="admin-check"><input type="checkbox" :checked="form.config.durations.includes(duration)" @change="toggleDuration(duration, $event.target.checked)" /><span>{{ duration }} 秒</span></label></div>
        </section>

        <label v-if="isUgc" class="admin-field"><span>业务指令块</span><AppTextarea v-model="form.config.business_instruction" rows="6" maxlength="6000" required /></label>
        <label v-if="isUgc" class="admin-field"><span>Provider 系统指令</span><AppTextarea v-model="form.config.provider_instruction" rows="4" maxlength="2000" required /></label>

        <section class="admin-template-block">
          <header><strong>Prompt 区块</strong><small>动态变量不可删除、改名或新增</small></header>
          <div class="admin-prompt-blocks">
            <label v-for="([key, label, variables]) in currentPromptFields" :key="key" class="admin-field">
              <span>{{ label }}<code v-if="variables">{{ variables }}</code></span>
              <AppTextarea v-model="form.config.prompt_blocks[key]" rows="5" maxlength="12000" :required="isUgc" />
            </label>
          </div>
        </section>

        <section class="admin-template-block">
          <header><strong>分镜连续性</strong><small>协议 ID 固定为 cut / extend</small></header>
          <div v-for="mode in ['cut', 'extend']" :key="mode" class="admin-continuity-row">
            <code>{{ mode }}</code>
            <AppInput v-model="form.config.continuity[mode].label" maxlength="32" :aria-label="`${mode} 展示名称`" />
            <AppInput v-model="form.config.continuity[mode].description" maxlength="120" :aria-label="`${mode} 说明`" />
          </div>
        </section>
      </template>

      <label class="admin-field"><span>操作原因</span><AppInput v-model="reason" maxlength="255" required placeholder="填写本次调整原因" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="saving || !reason.trim()">{{ saving ? '保存中…' : '保存内容模板' }}</AppButton><AppButton type="button" variant="soft" :disabled="saving" @click="load"><RefreshCw :size="15" />恢复已保存版本</AppButton></div>
    </form>
  </section>
</template>
