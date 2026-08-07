<script setup>
import AppButton from './AppButton.vue'

defineOptions({ inheritAttrs: false })

defineProps({
  modelValue: { type: [String, Number], required: true },
  options: { type: Array, required: true },
  ariaLabel: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div v-bind="$attrs" class="ui-tabs" role="tablist" :aria-label="ariaLabel">
    <AppButton
      v-for="option in options"
      :key="option.value"
      :as="option.to ? 'RouterLink' : 'button'"
      :to="option.to"
      type="button"
      role="tab"
      :disabled="option.disabled"
      :aria-selected="modelValue === option.value"
      :class="{ active: modelValue === option.value }"
      @click="!option.to && emit('update:modelValue', option.value)"
    >
      <component :is="option.icon" v-if="option.icon" :size="14" />
      {{ option.label }}
    </AppButton>
  </div>
</template>
