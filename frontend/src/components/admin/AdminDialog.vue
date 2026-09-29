<script setup>
import { X } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'
import AppTextarea from '../ui/AppTextarea.vue'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  confirmText: { type: String, default: null },
  cancelText: { type: String, default: null },
  submitting: Boolean,
  reasonRequired: { type: Boolean, default: true },
  reason: { type: String, default: '' },
  danger: Boolean,
})
const emit = defineEmits(['close', 'submit', 'update:reason'])
</script>

<template>
  <Teleport to="body">
    <div class="admin-dialog-backdrop" @pointerdown.self="emit('close')">
      <section class="admin-dialog" role="dialog" aria-modal="true" :aria-label="title">
        <header><div><h2>{{ title }}</h2><p v-if="description">{{ description }}</p></div><AppButton icon-only :aria-label="$t('common.close')" @click="emit('close')"><X :size="17" /></AppButton></header>
        <form @submit.prevent="emit('submit')">
          <div class="admin-dialog__body"><slot /></div>
          <label v-if="reasonRequired" class="admin-field"><span>{{ $t('common.reason') }}</span><AppTextarea :model-value="reason" rows="3" maxlength="255" required :placeholder="$t('common.reasonPlaceholder')" @update:model-value="emit('update:reason', $event)" /></label>
          <footer><AppButton v-if="cancelText !== ''" type="button" variant="soft" @click="emit('close')">{{ cancelText ?? $t('common.cancel') }}</AppButton><AppButton type="submit" :variant="danger ? 'danger' : 'primary'" :disabled="submitting || (reasonRequired && !reason.trim())">{{ submitting ? $t('common.submitting') : confirmText ?? $t('common.save') }}</AppButton></footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>
