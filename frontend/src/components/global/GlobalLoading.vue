<script setup>
import { LoaderCircle } from 'lucide-vue-next'
import { useGlobalLoading } from '../../composables/useGlobalLoading'

const { visible, message } = useGlobalLoading()
</script>

<template>
  <Teleport to="body">
    <Transition name="global-loading">
      <div v-if="visible" class="global-loading-backdrop" role="status" aria-live="polite">
        <div class="global-loading-indicator">
          <LoaderCircle :size="22" />
          <span>{{ message }}</span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
