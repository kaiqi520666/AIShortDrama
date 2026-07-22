<script setup>
import { ArrowRight, Clapperboard, Play, Sparkles } from 'lucide-vue-next'
import AppButton from '../components/ui/AppButton.vue'
import heroVisual from '../assets/mooncut-hero.webp'
</script>

<template>
  <main class="home-page">
    <header class="public-header">
      <RouterLink class="workspace-brand" to="/"><Clapperboard :size="20" /><strong>Mooncut</strong></RouterLink>
      <nav>
        <RouterLink to="/login">登录</RouterLink>
        <AppButton as="RouterLink" to="/register" variant="primary" size="sm">开始创作<ArrowRight :size="15" /></AppButton>
      </nav>
    </header>
    <section class="home-hero">
      <div class="home-reel" aria-hidden="true">
        <img :src="heroVisual" alt="" />
      </div>
      <div class="home-content">
        <span class="home-kicker"><Sparkles :size="14" />AI SHORT DRAMA STUDIO</span>
        <h1>Mooncut</h1>
        <p>把灵感、分镜与生成素材放进同一张画布，让每个镜头自然衔接。</p>
        <div class="home-actions">
          <AppButton as="RouterLink" to="/register" variant="primary" size="lg">创建工作台<ArrowRight :size="18" /></AppButton>
          <AppButton as="RouterLink" to="/login" variant="soft" size="lg"><Play :size="17" />继续项目</AppButton>
        </div>
      </div>
      <div class="home-meta"><span>TEXT</span><i></i><span>IMAGE</span><i></i><span>VIDEO</span><i></i><span>AUDIO</span></div>
    </section>
  </main>
</template>
