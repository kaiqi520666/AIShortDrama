<script setup>
import { Clapperboard, GitBranch } from 'lucide-vue-next'
</script>

<template>
  <header class="canvas-header">
    <div class="project-control">
      <div class="brand-mark"><Clapperboard :size="19" /></div>
      <span class="project-name">Mooncut</span>
      <span class="project-divider"></span>
      <span class="project-select">电商视觉工作流</span>
    </div>

    <div class="view-switch" role="tablist" aria-label="项目视图">
      <span class="active"><GitBranch :size="14" />工作流</span>
    </div>
  </header>
</template>
