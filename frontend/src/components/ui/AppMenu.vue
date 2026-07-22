<script setup>
import { ref } from 'vue'

defineOptions({ inheritAttrs: false })

const element = ref(null)
defineExpose({ element })
</script>

<template>
  <div ref="element" v-bind="$attrs" class="ui-menu" role="menu">
    <slot />
  </div>
</template>
