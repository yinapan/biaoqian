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
  if (isEffect.value) {
    // Effects: thumbnail_path is the GIF filename, show grid version by default
    const gifName = props.item.thumbnail_path
    const gridName = gifName.replace('.gif', '_grid.gif')
    return `/data/gifs/${gridName}`
  }
  return `/static/previews/${props.item.thumbnail_path}`
})

const isEffect = computed(() => store.moduleType === 2)

const displaySrc = computed(() => {
  if (isEffect.value && hovering.value && props.item.thumbnail_path) {
    // Hover: switch to normal (non-grid) GIF
    return `/data/gifs/${props.item.thumbnail_path}`
  }
  return thumbnailSrc.value
})

const visibleTags = computed(() => {
  const entries = Object.entries(props.item.tags)
  return entries
    .filter(([key]) => !['description', 'gif_duration_sec'].includes(key))
    .slice(0, 4)
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
  box-shadow: var(--shadow-card);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.asset-card:hover {
  border-color: var(--border-light);
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-1px);
}

/* --- Thumbnail --- */
.card-thumb {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--bg-root);
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 8px;
}

.asset-card:hover .card-thumb img {
  /* no zoom effect */
}

/* Hover overlay */
.thumb-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(17, 24, 39, 0.52) 0%,
    transparent 40%
  );
  opacity: 0;
  transition: opacity 0.15s ease;
}

.asset-card:hover .thumb-overlay {
  opacity: 1;
}

.overlay-action {
  display: none;
}

/* Floating badge */
.float-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 3px;
  background: rgba(16, 20, 24, 0.84);
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
}

/* --- Info section --- */
.card-info {
  padding: 11px 12px 12px;
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-subtle);
}

.card-name {
  font-size: 13px;
  font-weight: 650;
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
  gap: 5px;
}

.mini-tag {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 2px 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
