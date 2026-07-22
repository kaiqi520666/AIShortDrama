<script setup>
import { Inbox, LoaderCircle } from 'lucide-vue-next'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  loading: Boolean,
  compact: Boolean,
  tone: { type: String, default: 'default' },
})
</script>

<template>
  <section class="ui-empty-state" :class="[`ui-empty-state--${tone}`, { 'ui-empty-state--compact': compact }]">
    <LoaderCircle v-if="loading" class="ui-empty-state-spinner" :size="22" />
    <component :is="icon || Inbox" v-else :size="22" />
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.default" class="ui-empty-state-actions"><slot /></div>
  </section>
</template>
