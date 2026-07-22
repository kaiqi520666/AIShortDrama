<script setup>
defineOptions({ inheritAttrs: false })

defineProps({
  text: { type: String, required: true },
  placement: { type: String, default: 'top' },
})
</script>

<template>
  <span v-bind="$attrs" class="ui-tooltip" :data-placement="placement">
    <slot />
    <span class="ui-tooltip-content" role="tooltip">{{ text }}</span>
  </span>
</template>
