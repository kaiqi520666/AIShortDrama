<script setup>
import { ChevronDown } from 'lucide-vue-next'

defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  ariaLabel: { type: String, required: true },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <label class="ui-select">
    <select :value="modelValue" :aria-label="ariaLabel" @change="$emit('update:modelValue', $event.target.value)">
      <option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option>
    </select>
    <ChevronDown :size="14" aria-hidden="true" />
  </label>
</template>
