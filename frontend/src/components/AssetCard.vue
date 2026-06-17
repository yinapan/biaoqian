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
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">' +
    '<rect width="200" height="200" fill="#1a1b20"/>' +
    '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#5c5a54" font-size="12" font-family="sans-serif">No Preview</text>' +
    '</svg>',
  )

const thumbnailSrc = computed(() => {
  if (!props.item.thumbnail_path) return PLACEHOLDER
  return `/static/previews/${props.item.thumbnail_path}`
})

const isEffect = computed(() => store.moduleType === 2)

const displaySrc = computed(() => {
  if (isEffect.value && hovering.value && props.item.thumbnail_path) {
    const baseName = props.item.name
    return `/static/previews/effects/${baseName}.gif`
  }
  return thumbnailSrc.value
})

const visibleTags = computed(() => {
  const entries = Object.entries(props.item.tags)
  return entries.slice(0, 3)
})

const tagLabel = computed(() => {
  const first = Object.values(props.item.tags)[0]
  if (!first) return ''
  return Array.isArray(first) ? first[0] : String(first)
})
</script>

<template>
  <div
    class="asset-card"
    @click="showDetail = true"
    @mouseenter="hovering = true"
    @mouseleave="hovering = false"
  >
    <!-- Thumbnail -->
    <div class="card-thumb">
      <img
        :src="displaySrc"
        :alt="item.name"
        loading="lazy"
        @error="($event.target as HTMLImageElement).src = PLACEHOLDER"
      />
      <div class="thumb-overlay">
        <span class="overlay-action">查看详情</span>
      </div>
      <!-- Floating tag badge -->
      <span v-if="tagLabel" class="float-badge">{{ tagLabel }}</span>
    </div>

    <!-- Info -->
    <div class="card-info">
      <div class="card-name" :title="item.name">{{ item.name }}</div>
      <div class="card-tags">
        <span
          v-for="[key, val] in visibleTags"
          :key="key"
          class="mini-tag"
        >
          {{ Array.isArray(val) ? val.join(', ') : val }}
        </span>
      </div>
    </div>
  </div>

  <AssetDetailModal v-model="showDetail" :item="item" />
</template>

<style scoped>
.asset-card {
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  animation: fadeInUp 0.4s ease both;
}

.asset-card:hover {
  border-color: var(--border-light);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card-hover);
}

/* --- Thumbnail --- */
.card-thumb {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  background: var(--bg-root);
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.asset-card:hover .card-thumb img {
  transform: scale(1.06);
}

/* Hover overlay */
.thumb-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(12, 13, 16, 0.8) 0%,
    transparent 50%
  );
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 16px;
  opacity: 0;
  transition: opacity 0.25s ease;
}

.asset-card:hover .thumb-overlay {
  opacity: 1;
}

.overlay-action {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-text);
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(232, 168, 56, 0.15);
  border: 1px solid rgba(232, 168, 56, 0.3);
  backdrop-filter: blur(8px);
}

/* Floating badge */
.float-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background: rgba(12, 13, 16, 0.7);
  color: var(--text-secondary);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
}

/* --- Info section --- */
.card-info {
  padding: 10px 12px 12px;
}

.card-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
  letter-spacing: -0.01em;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.mini-tag {
  font-size: 11px;
  color: var(--text-muted);
  padding: 1px 6px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 3px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
