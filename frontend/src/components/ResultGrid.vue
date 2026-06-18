<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'
import AssetCard from './AssetCard.vue'

const store = useSearchStore()
</script>

<template>
  <div class="result-grid">
    <!-- Summary bar -->
    <div class="result-bar">
      <div class="result-stats">
        <template v-if="!store.loading && store.response">
          <span class="stat-total">{{ store.total.toLocaleString() }}</span>
          <span class="stat-label">条结果</span>
          <span class="stat-time">{{ store.response.query_time_ms }}ms</span>
        </template>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="store.loading" class="grid loading-grid">
      <div v-for="i in 12" :key="i" class="skeleton-card">
        <div class="skeleton-thumb" />
        <div class="skeleton-body">
          <div class="skeleton-line w60" />
          <div class="skeleton-line w40" />
        </div>
      </div>
    </div>

    <!-- Results grid -->
    <div v-else-if="store.items.length" class="grid">
      <AssetCard
        v-for="item in store.items"
        :key="item.id"
        :item="item"
      />
    </div>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
      </div>
      <p class="empty-text">暂无搜索结果</p>
      <p class="empty-hint">尝试调整关键词或筛选条件</p>
    </div>
  </div>
</template>

<style scoped>
.result-grid {
  min-height: 0;
}

/* --- Summary bar --- */
.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.result-stats {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: var(--font-mono);
}

.stat-total {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  font-family: var(--font-sans);
}

.stat-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}

/* --- Grid --- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}

/* --- Skeleton loading --- */
.skeleton-card {
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
}

.skeleton-thumb {
  aspect-ratio: 1;
  background: linear-gradient(
    90deg,
    var(--bg-surface) 25%,
    var(--bg-surface-hover) 50%,
    var(--bg-surface) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 10px;
  border-radius: 5px;
  background: var(--bg-surface-hover);
}

.skeleton-line.w60 { width: 60%; }
.skeleton-line.w40 { width: 40%; }

/* --- Empty state --- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 72px 0;
  gap: 12px;
}

.empty-icon {
  opacity: 0.3;
  margin-bottom: 8px;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}

@media (max-width: 720px) {
  .grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }
}

.empty-hint {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
