<script setup>
import { computed, ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import AppInput from '../ui/AppInput.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: String, default: '' },
  modelModifiers: { type: Object, default: () => ({}) },
  label: { type: String, required: true },
  icon: { type: [Object, Function], required: true },
  type: { type: String, default: 'text' },
  revealable: Boolean,
})
const emit = defineEmits(['update:modelValue'])
const revealed = ref(false)
const inputType = computed(() => props.revealable && revealed.value ? 'text' : props.type)

function updateValue(value) {
  emit('update:modelValue', props.modelModifiers.trim ? value.trim() : value)
}
</script>

<template>
  <label class="auth-field">
    <span class="auth-field-label">{{ label }}</span>
    <span class="auth-field-control">
      <component :is="icon" class="auth-field-icon" :size="17" aria-hidden="true" />
      <AppInput v-bind="$attrs" :model-value="modelValue" :type="inputType" :aria-label="label" @update:model-value="updateValue" />
      <button
        v-if="revealable"
        class="auth-password-toggle"
        type="button"
        :aria-label="revealed ? '隐藏密码' : '显示密码'"
        :aria-pressed="revealed"
        @click="revealed = !revealed"
      >
        <EyeOff v-if="revealed" :size="16" />
        <Eye v-else :size="16" />
      </button>
    </span>
  </label>
</template>
