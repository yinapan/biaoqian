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
const assetIdCopied = ref(false)

const PLACEHOLDER = 'data:image/svg+xml;charset=UTF-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">' +
    '<rect width="200" height="200" fill="#1a1b20"/>' +
    '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#5c5a54" font-size="12" font-family="sans-serif">No Preview</text>' +
    '</svg>',
  )

const isEffect = computed(() => store.moduleType === 2)
const isIcon = computed(() => store.moduleType === 4)
const isModel = computed(() => store.moduleType === 1)
const isAnimator = computed(() => store.moduleType === 3)

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
  if (isModel.value) {
    return `/static/previews/model/${props.item.thumbnail_path}`
  }
  if (isAnimator.value) {
    return `/static/previews/animator/${props.item.thumbnail_path}`
  }
  return `/static/previews/${props.item.thumbnail_path}`
})

const displaySrc = computed(() => {
  if (isEffect.value && hovering.value && props.item.thumbnail_path) {
    return `/data/gifs/${props.item.thumbnail_path}`
  }
  return thumbnailSrc.value
})

const assetId = computed(() => {
  if (isIcon.value) return String(props.item.tags?.icon_id ?? props.item.name)
  return ''
})

const showIdRow = computed(() => isIcon.value)

const CARD_HIDDEN_TAG_FIELDS = new Set([
  'description',
  'layout',
  'gif_duration_sec',
  'gif_front_path',
  'gif_left_path',
  'size_bytes',
  'action_id',
  'icon_id',
  'framed',
  'width_px',
  'height_px',
  'length_cm',
  'width_cm',
  'height_cm',
  'camera_distance',
  'camera_scale',
  'area_ratio',
  'span_max',
  'effect_duration_sec',
  'tag_source',
  'related_items',
  '__svn',
  '__source_version',
])

const visibleTags = computed(() => {
  const entries = Object.entries(props.item.tags)
  return entries
    .filter(([key]) => !CARD_HIDDEN_TAG_FIELDS.has(key))
    .filter(([, val]) => {
      if (Array.isArray(val)) {
        return val.every((item) => ['string', 'number', 'boolean'].includes(typeof item))
      }
      return ['string', 'number', 'boolean'].includes(typeof val)
    })
    .slice(0, 4)
})

function copyAssetId(event: MouseEvent) {
  event.stopPropagation()
  const text = assetId.value
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  } else {
    fallbackCopy(text)
  }
  assetIdCopied.value = true
  setTimeout(() => (assetIdCopied.value = false), 1500)
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
        fetchpriority="low"
        @error="($event.target as HTMLImageElement).src = PLACEHOLDER"
      />
      <div class="thumb-overlay">
        <span class="overlay-action">查看详情</span>
      </div>
      <!-- ID copy chip - appears on hover -->
      <Transition name="copy-fade">
        <button
          v-if="showIdRow && hovering"
          class="id-copy-chip"
          :class="{ copied: assetIdCopied }"
          @click="copyAssetId"
        >
          <span class="chip-label">ID</span>
          <span class="chip-value">{{ assetId }}</span>
          <span class="chip-action">
            <svg v-if="!assetIdCopied" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="14" height="14" rx="2.5"/><path d="M4 16H3a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v1"/></svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
        </button>
      </Transition>
    </div>

    <!-- Info -->
    <div class="card-info">
      <div class="card-name" :title="item.name">{{ item.name }}</div>

      <!-- Asset ID row (icon & animator) -->
      <div v-if="showIdRow" class="card-icon-id" @click.stop="copyAssetId($event)">
        <div class="id-pill">
          <span class="id-pill-label">ID</span>
          <code class="id-pill-value">{{ assetId }}</code>
        </div>
        <span class="id-pill-hint" :class="{ show: assetIdCopied }">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          已复制
        </span>
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

  <AssetDetailModal v-if="showDetail" v-model="showDetail" :item="item" />
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

/* ID copy chip (top-right overlay) */
.id-copy-chip {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 4px 0 10px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(8px);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}

.id-copy-chip:hover {
  background: rgba(23, 32, 42, 0.95);
  border-color: rgba(79, 156, 175, 0.45);
  box-shadow: 0 0 12px rgba(79, 156, 175, 0.12);
}

.id-copy-chip.copied {
  background: rgba(22, 163, 74, 0.18);
  border-color: rgba(34, 197, 94, 0.4);
  box-shadow: 0 0 16px rgba(34, 197, 94, 0.14);
}

.chip-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  transition: color 0.2s;
}

.id-copy-chip:hover .chip-label {
  color: var(--accent-text);
}

.id-copy-chip.copied .chip-label {
  color: #4ade80;
}

.chip-value {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}

.id-copy-chip:hover .chip-value {
  color: var(--text-primary);
}

.chip-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: rgba(226, 232, 240, 0.06);
  color: var(--text-muted);
  transition: all 0.2s;
}

.id-copy-chip:hover .chip-action {
  background: var(--accent);
  color: var(--text-on-accent);
}

.id-copy-chip.copied .chip-action {
  background: rgba(34, 197, 94, 0.25);
  color: #4ade80;
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
  justify-content: space-between;
  margin-bottom: 7px;
  cursor: pointer;
  user-select: none;
}

.id-pill {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition: all 0.2s ease;
}

.card-icon-id:hover .id-pill {
  border-color: rgba(79, 156, 175, 0.35);
  box-shadow: 0 0 0 1px rgba(79, 156, 175, 0.08);
}

.id-pill-label {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent-text);
  background: var(--accent-soft);
  border-right: 1px solid var(--border-subtle);
  flex-shrink: 0;
  transition: all 0.2s;
}

.card-icon-id:hover .id-pill-label {
  background: rgba(79, 156, 175, 0.22);
}

.id-pill-value {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 450;
  color: var(--text-secondary);
  padding: 4px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  transition: color 0.2s;
}

.card-icon-id:hover .id-pill-value {
  color: var(--text-primary);
}

.id-pill-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 8px;
  font-size: 11px;
  font-weight: 550;
  color: #4ade80;
  opacity: 0;
  transform: translateX(-6px);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: none;
}

.id-pill-hint.show {
  opacity: 1;
  transform: translateX(0);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-height: 45px;
  max-height: 45px;
  overflow: hidden;
  align-content: flex-start;
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
