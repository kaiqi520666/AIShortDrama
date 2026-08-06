<script setup>
import { ref } from 'vue'
import { ArrowUp, ChevronDown, Coins, LoaderCircle } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

defineProps({
  model: { type: Object, required: true },
  modelIcon: { required: true },
  modelSelectable: Boolean,
  modelOpen: Boolean,
  estimatedCredits: { type: Number, default: null },
  creditLabel: { type: String, default: '' },
  running: Boolean,
  disabled: Boolean,
})
const emit = defineEmits(['toggle-model', 'submit'])
const element = ref(null)

defineExpose({ element })
</script>

<template>
  <AppButton v-if="modelSelectable" ref="element" class="model-select model-select-trigger" @click="emit('toggle-model')">
    <component :is="modelIcon" :size="16" />{{ model.label }}<ChevronDown :size="14" :class="{ rotated: modelOpen }" />
  </AppButton>
  <span v-else class="model-select"><component :is="modelIcon" :size="16" />{{ model.label }}</span>
  <span v-if="estimatedCredits !== null" class="task-credit-cost"><Coins :size="14" />{{ creditLabel }}</span>
  <AppButton class="run-task-button" icon-only variant="primary" :disabled="disabled" :title="running ? '执行中' : '执行'" @click="emit('submit')">
    <LoaderCircle v-if="running" class="run-task-spinner" :size="20" />
    <ArrowUp v-else :size="20" />
  </AppButton>
</template>
