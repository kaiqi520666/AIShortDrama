<script setup>
import { ArrowRight, Clapperboard } from 'lucide-vue-next'
</script>

<template>
  <main class="auth-page home-page">
    <header class="public-header">
      <RouterLink class="workspace-brand" to="/"><Clapperboard :size="20" /><strong>Mooncut</strong></RouterLink>
      <nav><RouterLink to="/login">登录</RouterLink><RouterLink class="primary-link" to="/register">开始使用</RouterLink></nav>
    </header>
    <section class="home-content">
      <span>AI 视觉工作流</span>
      <h1>Mooncut</h1>
      <p>在一张画布中组织文本、图片、视频与音频生成流程。</p>
      <RouterLink class="home-action" to="/register">创建工作台<ArrowRight :size="18" /></RouterLink>
    </section>
  </main>
</template>
