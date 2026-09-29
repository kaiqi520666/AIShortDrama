<script setup>
import { computed } from 'vue'
import { Languages } from 'lucide-vue-next'
import AppSelect from './AppSelect.vue'
import { i18n, setLocale } from '../../i18n'

const locale = computed(() => i18n.global.locale.value)
const options = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'id', label: 'Bahasa Indonesia' },
]

</script>

<template>
  <div class="language-select">
    <Languages class="language-select-icon" :size="16" aria-hidden="true" />
    <AppSelect :model-value="locale" :options="options" :aria-label="$t('common.language')" @update:model-value="setLocale" />
  </div>
</template>

<style scoped>
.language-select { position: relative; width: 168px; max-width: 100%; flex-shrink: 0; }
.language-select-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); z-index: 1; pointer-events: none; }
.language-select :deep(.ui-select-trigger) { padding-left: 32px; }
@media (max-width: 360px) {
  .language-select { width: 36px; }
  .language-select :deep(.ui-select-trigger) { width: 36px; height: 36px; padding: 0; }
  .language-select :deep(.ui-select-trigger > span),
  .language-select :deep(.ui-select-trigger > svg) { display: none; }
  .language-select :deep(.ui-select-menu) { min-width: 168px; left: auto; right: 0; }
}
</style>
