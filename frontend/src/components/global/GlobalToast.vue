<script setup>
import { CheckCircle2, CircleAlert, Info, TriangleAlert, X } from 'lucide-vue-next'
import { useGlobalToast } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'

const icons = { success: CheckCircle2, error: CircleAlert, warning: TriangleAlert, info: Info }
const { toasts, removeToast } = useGlobalToast()
</script>

<template>
  <Teleport to="body">
    <div class="global-toast-stack" aria-live="polite" :aria-label="$t('canvas.notifications')">
      <TransitionGroup name="global-toast">
        <article v-for="item in toasts" :key="item.id" class="global-toast" :class="`global-toast--${item.type}`" :role="item.type === 'error' ? 'alert' : 'status'">
          <component :is="icons[item.type]" :size="18" />
          <p>{{ item.message }}</p>
          <AppButton icon-only size="sm" :title="$t('common.close')" @click="removeToast(item.id)"><X :size="14" /></AppButton>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
