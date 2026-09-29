<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
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

const props = defineProps({
  templateKey: { type: String, required: true },
  section: { type: String, required: true },
})

const { t, n } = useI18n()
const durationOptions = [15, 30, 45, 60]
const imageOptions = computed(() => [
  { value: 'product_visual', label: t('admin.templates.labels.product_visual'), to: { name: 'admin-image-product' } },
  { value: 'apparel_visual', label: t('admin.templates.labels.apparel_visual'), to: { name: 'admin-image-apparel' } },
])
const commerceOptions = computed(() => [
  { value: 'product_storyboard', label: t('admin.templates.labels.product_storyboard'), to: { name: 'admin-commerce-ugc' } },
  { value: 'commerce_drama', label: t('admin.templates.labels.commerce_drama'), to: { name: 'admin-commerce-drama' } },
])
const templateLabel = computed(() => t(`admin.templates.labels.${props.templateKey}`))
const promptFields = {
  product_visual: [
    ['task_instruction', '{types} {aspect_ratio} {resolution}'],
    ['output_protocol', ''],
  ],
  apparel_visual: [
    ['task_instruction', '{aspect_ratio} {resolution}'],
    ['fidelity_rules', ''],
    ['output_protocol', ''],
  ],
  product_storyboard: [
    ['director_role', ''],
    ['shooting_style', ''],
    ['dialogue_no_character', ''],
    ['dialogue_with_characters', '{character_count} {speaker_examples}'],
    ['image_rules', '{columns} {rows} {ratio}'],
    ['video_rules', '{ratio}'],
    ['first_segment_rule', '{segment}'],
    ['extend_segment_rule', '{segment} {previous_segment}'],
  ],
  commerce_drama: [
    ['creative_direction', ''],
    ['story_structure', '{segment_count}'],
    ['character_rules', '{character_count}'],
    ['dialogue_rules', '{speaker_examples}'],
    ['product_placement_rules', ''],
    ['image_rules', '{columns} {rows} {ratio}'],
    ['video_rules', '{ratio}'],
    ['continuity_rules', ''],
    ['forbidden_rules', ''],
  ],
  apparel_showcase: [
    ['look_rules', ''],
    ['model_rules', '{model_description}'],
    ['scene_rules', '{scene_description}'],
    ['phone_style_rules', ''],
    ['action_rules', ''],
    ['video_reference_rules', ''],
    ['sound_rules', ''],
    ['continuation_rules', '{duration}'],
    ['forbidden_rules', ''],
  ],
}

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const form = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const reason = ref('')
let loadSequence = 0

const isImageSettings = computed(() => props.section === 'image')
const isUgc = computed(() => props.templateKey === 'product_storyboard')
const isDrama = computed(() => props.templateKey === 'commerce_drama')
const isApparelShowcase = computed(() => props.templateKey === 'apparel_showcase')
const currentPromptFields = computed(() => promptFields[props.templateKey] || [])
const visibleDurationOptions = computed(() => isDrama.value ? durationOptions.slice(1) : durationOptions)
const pageCopy = computed(() => {
  if (isImageSettings.value) return { eyebrow: t('navigation.content'), title: t('navigation.imageSettings'), description: t('admin.templates.imageDescription') }
  if (isApparelShowcase.value) return { eyebrow: t('navigation.content'), title: templateLabel.value, description: t('admin.templates.apparelDescription') }
  return { eyebrow: t('navigation.content'), title: t('navigation.commerceTemplates'), description: t('admin.templates.commerceDescription') }
})

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

async function load() {
  const sequence = ++loadSequence
  loading.value = true
  error.value = ''
  form.value = null
  try {
    const result = await getAdminContentTemplate(props.templateKey)
    if (result.code !== 0) throw new Error(result.message)
    if (sequence !== loadSequence) return
    form.value = clone(result.data)
    reason.value = ''
  } catch (requestError) {
    if (sequence !== loadSequence) return
    error.value = getApiErrorMessage(requestError, t('admin.templates.loadFailed', { name: templateLabel.value }))
    toast.error(error.value)
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

function toggleDuration(duration, checked) {
  const durations = form.value.config.durations
  form.value.config.durations = checked
    ? [...new Set([...durations, duration])].sort((a, b) => a - b)
    : durations.filter((item) => item !== duration)
}

async function save() {
  const label = templateLabel.value
  const payload = { enabled: form.value.enabled, config: form.value.config, reason: reason.value }
  if (!await confirmMutation({
    title: t('admin.templates.update', { name: label }),
    message: t('admin.templates.confirmation', { name: label }),
  })) return
  saving.value = true
  try {
    const result = await updateAdminContentTemplate(props.templateKey, payload)
    if (result.code !== 0) throw new Error(result.message)
    form.value = clone(result.data)
    reason.value = ''
    toast.success(t('admin.templates.updated', { name: label }))
  } catch (requestError) {
    toast.error(getApiErrorMessage(requestError, t('admin.templates.saveFailed', { name: label })))
  } finally {
    saving.value = false
  }
}

watch(() => props.templateKey, load)
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header">
      <div><span>{{ pageCopy.eyebrow }}</span><h1>{{ pageCopy.title }}</h1><p>{{ pageCopy.description }}</p></div>
      <b v-if="form">{{ templateLabel }} · v{{ form.version }}</b>
    </header>

    <nav v-if="isImageSettings" class="admin-template-subnav" :aria-label="t('admin.templates.imageType')">
      <AppTabs :model-value="templateKey" :options="imageOptions" :aria-label="t('admin.templates.imageType')" />
    </nav>
    <nav v-else-if="!isApparelShowcase" class="admin-template-subnav" :aria-label="t('admin.templates.commerceType')">
      <AppTabs :model-value="templateKey" :options="commerceOptions" :aria-label="t('admin.templates.commerceType')" />
    </nav>

    <EmptyState v-if="error" tone="error" :title="t('admin.templates.loadFailed', { name: templateLabel })" :description="error"><AppButton variant="primary" @click="load">{{ t('common.reload') }}</AppButton></EmptyState>
    <EmptyState v-else-if="loading || !form" loading :title="t('admin.templates.loading', { name: templateLabel })" />
    <form v-else class="admin-template-form" @submit.prevent="save">
      <div class="admin-template-form__top">
        <label class="admin-check"><input v-model="form.enabled" type="checkbox" /><span>{{ t(isImageSettings ? 'admin.templates.enableSettings' : 'admin.templates.enableTemplate') }}</span></label>
        <small>{{ t('admin.templates.futureOnly') }}</small>
      </div>

      <template v-if="isImageSettings">
        <section v-for="group in form.config.groups || []" :key="group.id" class="admin-template-block">
          <header><AppInput v-model="group.label" maxlength="64" :aria-label="t('admin.templates.groupName', { id: group.id })" /><small>{{ group.id }}</small></header>
          <div class="admin-template-items">
            <label v-for="item in group.items" :key="item.id" class="admin-template-item">
              <AppInput v-model="item.label" maxlength="64" :aria-label="t('admin.templates.imageName', { id: item.id })" />
              <span>{{ item.id }}</span>
              <span class="admin-check"><input v-model="item.default_enabled" type="checkbox" /><i><Check :size="13" /></i>{{ t('admin.templates.defaultEnabled') }}</span>
            </label>
          </div>
        </section>
        <section v-if="templateKey === 'apparel_visual'" class="admin-template-block">
          <header><strong>{{ t('admin.templates.outputTarget') }}</strong><small>{{ t('admin.templates.oneImage') }}</small></header>
          <div class="admin-protocol-row"><code>{{ t('admin.templates.frontFullBody') }}</code><p>{{ t('admin.templates.apparelTarget') }}</p></div>
        </section>
        <label class="admin-field"><span>{{ t('admin.templates.businessInstruction') }}</span><AppTextarea v-model="form.config.business_instruction" rows="6" maxlength="6000" :placeholder="t(templateKey === 'apparel_visual' ? 'admin.templates.apparelPlaceholder' : 'admin.templates.productPlaceholder')" /></label>
        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.modelPrompt') }}</strong><small>{{ t('admin.templates.fixedVariables') }}</small></header>
          <label class="admin-field"><span>{{ t('admin.templates.providerInstruction') }}</span><AppTextarea v-model="form.config.provider_instruction" rows="4" maxlength="2000" required /></label>
          <div class="admin-prompt-blocks">
            <label v-for="([key, variables]) in currentPromptFields" :key="key" class="admin-field">
              <span>{{ t(`admin.templates.fields.${key}`) }}<code v-if="variables">{{ variables }}</code></span>
              <AppTextarea v-model="form.config.prompt_blocks[key]" rows="6" maxlength="12000" required />
            </label>
          </div>
        </section>
        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.jsonProtocol') }}</strong><small>{{ t('admin.templates.fixedProtocol') }}</small></header>
          <div class="admin-protocol-row"><code>{{ form.config.output_protocol_id }}</code><p>{{ t(templateKey === 'apparel_visual' ? 'admin.templates.apparelProtocol' : 'admin.templates.productProtocol') }}</p></div>
        </section>
      </template>

      <template v-else>
        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.basic', { name: templateLabel }) }}</strong><small>{{ isUgc ? form.config.templates[0].id : form.config.output_protocol_id }}</small></header>
          <div v-if="isUgc" class="admin-form-grid">
            <label class="admin-field"><span>{{ t('admin.templates.name') }}</span><AppInput v-model="form.config.templates[0].label" maxlength="64" /></label>
            <label class="admin-field"><span>{{ t('admin.templates.description') }}</span><AppInput v-model="form.config.templates[0].description" maxlength="255" /></label>
          </div>
          <div v-else class="admin-form-grid">
            <label class="admin-field"><span>{{ t('admin.templates.name') }}</span><AppInput v-model="form.config.label" maxlength="64" /></label>
            <label class="admin-field"><span>{{ t('admin.templates.description') }}</span><AppInput v-model="form.config.description" maxlength="255" /></label>
          </div>
          <label v-if="isUgc" class="admin-check"><input v-model="form.config.templates[0].enabled" type="checkbox" /><span>{{ t('admin.templates.ugcEnabled') }}</span></label>
        </section>

        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.durations') }}</strong><small>{{ t('admin.templates.segmentDuration') }}</small></header>
          <div class="admin-duration-options"><label v-for="duration in visibleDurationOptions" :key="duration" class="admin-check"><input type="checkbox" :checked="form.config.durations.includes(duration)" @change="toggleDuration(duration, $event.target.checked)" /><span>{{ t('admin.templates.seconds', { count: n(duration) }) }}</span></label></div>
        </section>

        <label v-if="isUgc" class="admin-field"><span>{{ t('admin.templates.businessInstruction') }}</span><AppTextarea v-model="form.config.business_instruction" rows="6" maxlength="6000" required /></label>
        <label class="admin-field"><span>{{ t('admin.templates.providerInstruction') }}</span><AppTextarea v-model="form.config.provider_instruction" rows="4" maxlength="2000" required /></label>

        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.jsonProtocol') }}</strong><small>{{ t('admin.templates.fixedProtocol') }}</small></header>
          <div class="admin-protocol-row">
            <code>{{ isUgc ? 'ugc-seeding' : form.config.output_protocol_id }}</code>
            <p>{{ t(isUgc ? 'admin.templates.ugcProtocol' : isApparelShowcase ? 'admin.templates.showcaseProtocol' : 'admin.templates.dramaProtocol') }}</p>
          </div>
        </section>

        <section class="admin-template-block">
          <header><strong>{{ t('admin.templates.blocks') }}</strong><small>{{ t('admin.templates.fixedVariables') }}</small></header>
          <div class="admin-prompt-blocks">
            <label v-for="([key, variables]) in currentPromptFields" :key="key" class="admin-field">
              <span>{{ t(`admin.templates.fields.${key}`) }}<code v-if="variables">{{ variables }}</code></span>
              <AppTextarea v-model="form.config.prompt_blocks[key]" rows="5" maxlength="12000" required />
            </label>
          </div>
        </section>

        <section v-if="!isApparelShowcase" class="admin-template-block">
          <header><strong>{{ t('admin.templates.continuity') }}</strong><small>{{ t('admin.templates.continuityIds') }}</small></header>
          <div v-for="mode in ['cut', 'extend']" :key="mode" class="admin-continuity-row">
            <code>{{ mode }}</code>
            <AppInput v-model="form.config.continuity[mode].label" maxlength="32" :aria-label="t('admin.templates.displayName', { id: mode })" />
            <AppInput v-model="form.config.continuity[mode].description" maxlength="120" :aria-label="t('admin.templates.displayDescription', { id: mode })" />
          </div>
        </section>
      </template>

      <label class="admin-field"><span>{{ t('common.reason') }}</span><AppInput v-model="reason" maxlength="255" required :placeholder="t('common.reasonPlaceholder')" /></label>
      <div class="admin-form-actions"><AppButton type="submit" variant="primary" :disabled="saving || !reason.trim()">{{ saving ? t('common.saving') : t('admin.templates.save', { name: templateLabel }) }}</AppButton><AppButton type="button" variant="soft" :disabled="saving" @click="load"><RefreshCw :size="15" />{{ t('admin.templates.restore') }}</AppButton></div>
    </form>
  </section>
</template>
