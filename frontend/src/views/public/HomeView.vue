<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { animate } from 'motion/mini'
import { ArrowRight, LogIn, Play, Sparkles } from 'lucide-vue-next'
import AppBrand from '../../components/ui/AppBrand.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppLanguageSelect from '../../components/ui/AppLanguageSelect.vue'
import heroVisual from '../../assets/mooncut-commerce-hero.webp'

const pageHeader = ref(null)
const hero = ref(null)
const reel = ref(null)
const content = ref(null)
const meta = ref(null)
let animations = []
let pointerFrame = null
let motionEnabled = false

function updateParallax(event) {
  if (!motionEnabled) return
  const bounds = hero.value.getBoundingClientRect()
  const x = ((event.clientX - bounds.left) / bounds.width - .5) * -14
  const y = ((event.clientY - bounds.top) / bounds.height - .5) * -8
  cancelAnimationFrame(pointerFrame)
  pointerFrame = requestAnimationFrame(() => {
    reel.value.style.setProperty('--hero-x', `${x}px`)
    reel.value.style.setProperty('--hero-y', `${y}px`)
  })
}

function resetParallax() {
  reel.value?.style.setProperty('--hero-x', '0px')
  reel.value?.style.setProperty('--hero-y', '0px')
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  motionEnabled = true
  const ease = [.16, 1, .3, 1]
  animations = [
    animate(pageHeader.value, { opacity: [0, 1], y: [-16, 0] }, { duration: .6, ease }),
    animate(reel.value, { scale: [1.02, 1.08] }, { duration: 18, ease: 'linear' }),
    ...Array.from(content.value.querySelectorAll('[data-reveal]')).map((element, index) =>
      animate(element, { opacity: [0, 1], y: [24, 0] }, { delay: .18 + index * .11, duration: .72, ease })),
    animate(meta.value, { opacity: [0, 1], x: [18, 0] }, { delay: .65, duration: .6, ease }),
  ]
})

onBeforeUnmount(() => {
  cancelAnimationFrame(pointerFrame)
  animations.forEach((animation) => animation.stop())
})
</script>

<template>
  <main class="home-page">
    <header ref="pageHeader" class="public-header">
      <AppBrand />
      <nav>
        <AppLanguageSelect />
        <AppButton class="home-login-button" as="RouterLink" to="/login" size="sm" :aria-label="$t('auth.login')"><LogIn :size="15" /><span>{{ $t('auth.login') }}</span></AppButton>
        <AppButton class="home-start-button" as="RouterLink" to="/register" variant="primary" size="sm">{{ $t('home.start') }}<ArrowRight :size="15" /></AppButton>
      </nav>
    </header>
    <section ref="hero" class="home-hero" @pointermove="updateParallax" @pointerleave="resetParallax">
      <div ref="reel" class="home-reel" aria-hidden="true">
        <img :src="heroVisual" alt="" />
      </div>
      <div ref="content" class="home-content">
        <span class="home-kicker" data-reveal><Sparkles :size="14" />{{ $t('home.studio') }}</span>
        <h1 data-reveal>{{ $t('home.headline') }}<br />{{ $t('home.workspace') }}</h1>
        <p data-reveal>{{ $t('home.description') }}</p>
        <div class="home-actions" data-reveal>
          <AppButton as="RouterLink" to="/register" variant="primary" size="lg">{{ $t('home.create') }}<ArrowRight :size="18" /></AppButton>
          <AppButton as="RouterLink" to="/login" variant="soft" size="lg"><Play :size="17" />{{ $t('home.continue') }}</AppButton>
        </div>
      </div>
      <div ref="meta" class="home-meta"><span>{{ $t('home.text') }}</span><i></i><span>{{ $t('home.image') }}</span><i></i><span>{{ $t('home.video') }}</span><i></i><span>{{ $t('home.audio') }}</span></div>
    </section>
  </main>
</template>
