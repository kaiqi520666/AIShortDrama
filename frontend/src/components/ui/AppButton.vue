<script setup>
defineOptions({ inheritAttrs: false })

defineProps({
  as: { type: [String, Object], default: 'button' },
  variant: { type: String, default: 'ghost' },
  size: { type: String, default: 'md' },
  iconOnly: Boolean,
  block: Boolean,
})
</script>

<template>
  <component
    :is="as"
    v-bind="$attrs"
    :class="['ui-button', `ui-button--${variant}`, `ui-button--${size}`, { 'ui-button--icon': iconOnly, 'ui-button--block': block }]"
  >
    <slot />
  </component>
</template>
