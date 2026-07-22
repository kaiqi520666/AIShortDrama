<script setup>
import { computed, ref } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: undefined },
  value: { type: [String, Number], default: '' },
  modelModifiers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue', 'input'])
const element = ref(null)
const inputValue = computed(() => props.modelValue ?? props.value)

function handleInput(event) {
  let value = event.target.value
  if (props.modelModifiers.trim) value = value.trim()
  if (props.modelModifiers.number) value = Number(value)
  emit('update:modelValue', value)
  emit('input', event)
}

defineExpose({ element, focus: () => element.value?.focus() })
</script>

<template>
  <input ref="element" v-bind="$attrs" class="ui-input" :value="inputValue" @input="handleInput" />
</template>
