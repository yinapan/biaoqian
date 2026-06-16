<script setup lang="ts">
import { computed } from 'vue'
import type { AssetItem } from '@/types'

const props = defineProps<{
  item: AssetItem
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const previewSrc = computed(() => {
  if (!props.item.thumbnail_path) return ''
  return `/static/previews/${props.item.thumbnail_path}`
})

const tagEntries = computed(() => Object.entries(props.item.tags))
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="item.name"
    width="680px"
    destroy-on-close
  >
    <div class="detail-content">
      <!-- Preview image -->
      <div v-if="previewSrc" class="detail-preview">
        <img :src="previewSrc" :alt="item.name" />
      </div>

      <!-- Tags -->
      <el-descriptions :column="2" border size="small" class="detail-tags">
        <el-descriptions-item
          v-for="[key, val] in tagEntries"
          :key="key"
          :label="key"
        >
          {{ Array.isArray(val) ? val.join(', ') : val }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- Resource path -->
      <div class="detail-path">
        <strong>资源路径：</strong>
        <el-text type="info" size="small">{{ item.resource_path }}</el-text>
      </div>

      <!-- Relevance score -->
      <div v-if="item.relevance_score" class="detail-score">
        <strong>相关度：</strong>
        {{ item.relevance_score.toFixed(2) }}
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-preview {
  text-align: center;
}

.detail-preview img {
  max-width: 100%;
  max-height: 400px;
  border-radius: 6px;
}

.detail-tags {
  width: 100%;
}

.detail-path,
.detail-score {
  font-size: 13px;
}
</style>
