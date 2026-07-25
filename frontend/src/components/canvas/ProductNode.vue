<script setup>
import { computed } from 'vue'
import { Package, Sparkles } from 'lucide-vue-next'
import { useVueFlow } from '@vue-flow/core'
import AppInput from '../ui/AppInput.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import StructuredNodeShell from './StructuredNodeShell.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const { updateNodeData } = useVueFlow()
const product = computed(() => props.data.product || {})
const completed = computed(() => ['name', 'category', 'sellingPoints'].filter((key) => product.value[key]?.trim()).length)

function updateField(key, value) {
  updateNodeData(props.id, { product: { ...product.value, [key]: value }, status: 'ready' })
}
</script>

<template>
  <StructuredNodeShell :id="id" :type="type" :data="data" :icon="Package" :selected="selected" has-target>
    <div class="product-node-content nodrag nopan nowheel" @keydown.stop>
      <div class="structured-node-summary">
        <span><Package :size="15" />商品档案</span>
        <small>{{ completed }}/3 核心信息</small>
      </div>
      <div class="product-fields two-columns">
        <label><span>商品名称</span><AppInput :model-value="product.name" placeholder="例如：轻量冲锋衣" @input="updateField('name', $event.target.value)" /></label>
        <label><span>品牌</span><AppInput :model-value="product.brand" placeholder="品牌名称" @input="updateField('brand', $event.target.value)" /></label>
        <label><span>品类</span><AppInput :model-value="product.category" placeholder="服饰 / 美妆 / 数码" @input="updateField('category', $event.target.value)" /></label>
        <label><span>价格</span><AppInput :model-value="product.price" placeholder="例如：¥299" @input="updateField('price', $event.target.value)" /></label>
      </div>
      <label class="product-field-wide"><span>规格 / SKU</span><AppInput :model-value="product.specifications" placeholder="颜色、尺码、容量等" @input="updateField('specifications', $event.target.value)" /></label>
      <label class="product-field-wide"><span>核心卖点</span><AppTextarea :model-value="product.sellingPoints" maxlength="800" placeholder="用换行分隔主要卖点" @input="updateField('sellingPoints', $event.target.value)" /></label>
      <div class="product-fields two-columns">
        <label><span>目标人群</span><AppInput :model-value="product.audience" placeholder="目标用户" @input="updateField('audience', $event.target.value)" /></label>
        <label><span>使用场景</span><AppInput :model-value="product.scenario" placeholder="通勤、户外等" @input="updateField('scenario', $event.target.value)" /></label>
      </div>
      <div class="structured-node-foot"><Sparkles :size="13" />{{ data.status === 'generating' ? '正在识别商品信息…' : '选中节点可 AI 识别商品信息' }}</div>
    </div>
  </StructuredNodeShell>
</template>
