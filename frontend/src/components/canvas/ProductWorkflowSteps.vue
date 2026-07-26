<script setup>
import { Check, ChevronRight } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

defineProps({
  step: { type: String, required: true },
  recognized: Boolean,
})

defineEmits(['update:step'])
</script>

<template>
  <nav class="product-workflow-steps" aria-label="商品创作步骤">
    <AppButton :class="{ active: step === 'recognition', complete: recognized }" @click.stop="$emit('update:step', 'recognition')">
      <span class="product-workflow-step-index"><Check v-if="recognized" :size="12" /><template v-else>1</template></span>
      <span>商品识别</span>
    </AppButton>
    <ChevronRight class="product-workflow-step-arrow" :size="15" />
    <AppButton :class="{ active: step === 'visual' }" :disabled="!recognized" @click.stop="$emit('update:step', 'visual')">
      <span class="product-workflow-step-index">2</span>
      <span>出图设置</span>
    </AppButton>
  </nav>
</template>
