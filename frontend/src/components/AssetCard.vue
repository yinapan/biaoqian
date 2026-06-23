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
const iconIdCopied = ref(false)

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
    const gifName = props.item.thumbnail_path
    const gridName = gifName.replace('.gif', '_grid.gif')
    return `/data/gifs/${gridName}`
  }
  if (isIcon.value) {
    return `/data/icons/${props.item.thumbnail_path}`
  }
  return `/static/previews/${props.item.thumbnail_path}`
})

const isEffect = computed(() => store.moduleType === 2)
const isIcon = computed(() => store.moduleType === 4)

const displaySrc = computed(() => {
  if (isEffect.value && hovering.value && props.item.thumbnail_path) {
    return `/data/gifs/${props.item.thumbnail_path}`
  }
  return thumbnailSrc.value
})

const iconId = computed(() => {
  if (!isIcon.value) return ''
  return props.item.name
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

function copyIconId(event: MouseEvent) {
  event.stopPropagation()
  const text = props.item.name
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  } else {
    fallbackCopy(text)
  }
  iconIdCopied.value = true
  setTimeout(() => (iconIdCopied.value = false), 1500)
}

function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
}
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
        decoding="async"
        @error="($event.target as HTMLImageElement).src = PLACEHOLDER"
      />
      <div class="thumb-overlay">
        <span class="overlay-action">查看详情</span>
      </div>
      <!-- Floating tag badge -->
      <span v-if="tagLabel" class="float-badge">{{ tagLabel }}</span>
      <!-- Icon copy button - appears on hover -->
      <Transition name="copy-fade">
        <button
          v-if="isIcon && hovering"
          class="icon-copy-btn"
          :class="{ copied: iconIdCopied }"
          @click="copyIconId"
          :title="iconIdCopied ? '已复制' : '复制 icon_id'"
        >
          <svg v-if="!iconIdCopied" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
        </button>
      </Transition>
    </div>

    <!-- Info -->
    <div class="card-info">
      <div class="card-name" :title="item.name">{{ item.name }}</div>

      <!-- Icon ID row for icon module -->
      <div v-if="isIcon" class="card-icon-id" @click.stop="copyIconId($event)">
        <span class="icon-id-label">ID</span>
        <code class="icon-id-value">{{ iconId }}</code>
        <span v-if="iconIdCopied" class="icon-id-copied">已复制</span>
      </div>

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
  content-visibility: auto;
  contain-intrinsic-size: 0 280px;
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

/* Icon copy button (top-right overlay) */
.icon-copy-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-light);
  border-radius: 5px;
  background: rgba(16, 20, 24, 0.88);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  backdrop-filter: blur(4px);
}

.icon-copy-btn:hover {
  background: var(--accent);
  color: var(--text-on-accent);
  border-color: var(--accent);
}

.icon-copy-btn.copied {
  background: rgba(34, 197, 94, 0.9);
  color: white;
  border-color: rgba(34, 197, 94, 0.9);
}

.copy-fade-enter-active,
.copy-fade-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}

.copy-fade-enter-from,
.copy-fade-leave-to {
  opacity: 0;
  transform: scale(0.85);
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

/* --- Icon ID row --- */
.card-icon-id {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding: 3px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.card-icon-id:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.icon-id-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 1px 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.icon-id-value {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.card-icon-id:hover .icon-id-value {
  color: var(--accent-text);
}

.icon-id-copied {
  font-size: 10px;
  font-weight: 600;
  color: #4ade80;
  flex-shrink: 0;
  animation: copied-pop 0.2s ease;
}

@keyframes copied-pop {
  0% { transform: scale(0.8); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
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
