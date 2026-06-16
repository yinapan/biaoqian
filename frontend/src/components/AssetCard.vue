<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { AssetItem } from '@/types'
import AssetDetailModal from './AssetDetailModal.vue'

const props = defineProps<{
  item: AssetItem
}>()

const store = useSearchStore()
const showDetail = ref(false)
const hovering = ref(false)

const PLACEHOLDER = 'data:image/svg+xml;charset=UTF-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" fill="%23e0e0e0">' +
    '<rect width="200" height="200"/>' +
    '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23999" font-size="14">No Preview</text>' +
    '</svg>',
  )

const thumbnailSrc = computed(() => {
  if (!props.item.thumbnail_path) return PLACEHOLDER
  return `/static/previews/${props.item.thumbnail_path}`
})

const isEffect = computed(() => store.moduleType === 2)

const displaySrc = computed(() => {
  if (isEffect.value && hovering.value && props.item.thumbnail_path) {
    // Replace extension with .gif for hover preview
    const baseName = props.item.name
    return `/static/previews/effects/${baseName}.gif`
  }
  return thumbnailSrc.value
})

// Show first 5 tag entries
const visibleTags = computed(() => {
  const entries = Object.entries(props.item.tags)
  return entries.slice(0, 5)
})
</script>

<template>
  <el-card
    class="asset-card"
    shadow="hover"
    :body-style="{ padding: '0' }"
    @click="showDetail = true"
    @mouseenter="hovering = true"
    @mouseleave="hovering = false"
  >
    <div class="card-thumb">
      <img
        :src="displaySrc"
        :alt="item.name"
        loading="lazy"
        @error="($event.target as HTMLImageElement).src = PLACEHOLDER"
      />
    </div>
    <div class="card-body">
      <div class="card-name" :title="item.name">{{ item.name }}</div>
      <div class="card-tags">
        <el-tag
          v-for="[key, val] in visibleTags"
          :key="key"
          size="small"
          type="info"
          effect="plain"
          class="tag-item"
        >
          {{ Array.isArray(val) ? val.join(', ') : val }}
        </el-tag>
      </div>
    </div>
  </el-card>

  <AssetDetailModal v-model="showDetail" :item="item" />
</template>

<style scoped>
.asset-card {
  margin-bottom: 16px;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
}

.card-thumb {
  width: 100%;
  aspect-ratio: 1;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-body {
  padding: 10px 12px;
}

.card-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-item {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
