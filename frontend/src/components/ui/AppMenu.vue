<script setup>
defineOptions({ inheritAttrs: false })
</script>

<template>
  <div v-bind="$attrs" class="ui-menu" role="menu">
    <slot />
  </div>
</template>
