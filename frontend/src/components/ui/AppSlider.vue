<script setup>
defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, required: true },
  max: { type: Number, required: true },
  step: { type: Number, default: 1 },
  label: { type: String, required: true },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="ui-slider">
    <span>{{ label }}</span>
    <input
      type="range"
      :value="modelValue"
      :min="min"
      :max="max"
      :step="step"
      :aria-label="label"
      @input="$emit('update:modelValue', Number($event.target.value))"
    />
    <output>{{ modelValue }}</output>
  </label>
</template>
