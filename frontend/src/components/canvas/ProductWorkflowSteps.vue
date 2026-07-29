<script setup>
import { Check, ChevronRight } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

defineProps({
  step: { type: String, required: true },
  recognized: Boolean,
  firstStep: { type: String, default: 'recognition' },
  secondStep: { type: String, default: 'visual' },
  firstLabel: { type: String, default: '商品识别' },
  secondLabel: { type: String, default: '出图设置' },
  ariaLabel: { type: String, default: '商品创作步骤' },
})

defineEmits(['update:step'])
</script>

<template>
  <nav class="product-workflow-steps" :aria-label="ariaLabel">
    <AppButton :class="{ active: step === firstStep, complete: recognized }" @click.stop="$emit('update:step', firstStep)">
      <span class="product-workflow-step-index"><Check v-if="recognized" :size="12" /><template v-else>1</template></span>
      <span>{{ firstLabel }}</span>
    </AppButton>
    <ChevronRight class="product-workflow-step-arrow" :size="15" />
    <AppButton :class="{ active: step === secondStep }" :disabled="!recognized" @click.stop="$emit('update:step', secondStep)">
      <span class="product-workflow-step-index">2</span>
      <span>{{ secondLabel }}</span>
    </AppButton>
  </nav>
</template>
