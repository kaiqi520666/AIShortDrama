<script setup>
import { computed, ref } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: undefined },
  value: { type: [String, Number], default: '' },
})
const emit = defineEmits(['update:modelValue', 'input'])
const element = ref(null)
const inputValue = computed(() => props.modelValue ?? props.value)

function handleInput(event) {
  emit('update:modelValue', event.target.value)
  emit('input', event)
}

defineExpose({ element, focus: () => element.value?.focus() })
</script>

<template>
  <textarea ref="element" v-bind="$attrs" class="ui-textarea" :value="inputValue" @input="handleInput"></textarea>
</template>
