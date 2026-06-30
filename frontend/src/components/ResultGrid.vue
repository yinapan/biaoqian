<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import AssetCard from './AssetCard.vue'

const store = useSearchStore()
const INITIAL_RENDER_LIMIT = 18
const RENDER_BATCH_SIZE = 12
const renderLimit = ref(INITIAL_RENDER_LIMIT)
let frameId: number | null = null

const MODULE_LABELS: Record<number, string> = {
  1: '模型',
  2: '特效',
  3: '动作',
  4: '图标',
}

const visibleItems = computed(() => store.items.slice(0, renderLimit.value))
const moduleLabel = computed(() => MODULE_LABELS[store.moduleType] ?? '当前')
const hasManualFilters = computed(() => Object.keys(store.filters).length > 0)
const hasActiveSearch = computed(() =>
  Boolean(store.query.trim()) ||
  hasManualFilters.value ||
  Boolean(store.parseInfo?.effective_filters && Object.keys(store.parseInfo.effective_filters).length) ||
  Boolean(store.parseInfo?.effective_excludes && Object.keys(store.parseInfo.effective_excludes).length),
)

const fieldNames = computed(() => {
  const names: Record<string, string> = {}
  for (const definition of store.tagDefinitions) {
    names[definition.field_name] = definition.display_name || definition.field_name
  }
  return names
})

const emptyTitle = computed(() =>
  hasActiveSearch.value ? '当前条件没有匹配资源' : `${moduleLabel.value}模块暂无资源`,
)

const emptyDescription = computed(() => {
  if (hasActiveSearch.value) {
    return `搜索已执行，但在${moduleLabel.value}模块没有命中。可以放宽关键词、减少筛选条件，或切换上方模块继续查找。`
  }
  return `当前${moduleLabel.value}模块还没有可展示资源。`
})

const emptyChips = computed(() => {
  const chips: Array<{ id: string; label: string; value: string; tone: string }> = []
  const query = store.query.trim()

  if (query) {
    chips.push({ id: 'query', label: '搜索词', value: query, tone: 'query' })
  }

  const addEntries = (source: Record<string, any> | undefined, label: string, tone: string) => {
    if (!source) return
    for (const [field, value] of Object.entries(source)) {
      chips.push({
        id: `${tone}-${field}`,
        label: `${label} ${fieldNames.value[field] ?? field}`,
        value: formatChipValue(value),
        tone,
      })
    }
  }

  if (store.parseInfo) {
    addEntries(store.parseInfo.effective_filters, '匹配', 'match')
    addEntries(store.parseInfo.effective_excludes, '排除', 'exclude')
  } else {
    addEntries(store.filters, '筛选', 'filter')
  }

  return chips.slice(0, 8)
})

function formatChipValue(value: any) {
  if (Array.isArray(value)) return value.join('、')
  if (value && typeof value === 'object') return Object.values(value).join('、')
  return String(value)
}

function clearSearchContext() {
  store.query = ''
  store.clearFilters()
  store.page = 1
  store.doSearch()
}

function clearQueryOnly() {
  store.query = ''
  store.dismissedFields.clear()
  store.page = 1
  store.doSearch()
}

watch(
  () => store.items,
  async (items) => {
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
      frameId = null
    }
    renderLimit.value = Math.min(INITIAL_RENDER_LIMIT, items.length)
    await nextTick()
    const renderNextBatch = () => {
      renderLimit.value = Math.min(renderLimit.value + RENDER_BATCH_SIZE, items.length)
      if (renderLimit.value < items.length) {
        frameId = requestAnimationFrame(renderNextBatch)
      } else {
        frameId = null
      }
    }
    if (renderLimit.value < items.length) {
      frameId = requestAnimationFrame(renderNextBatch)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (frameId !== null) cancelAnimationFrame(frameId)
})
</script>

<template>
  <div class="result-grid" data-testid="result-grid">
    <div class="result-bar">
      <div class="result-stats">
        <template v-if="!store.loading && store.response">
          <span class="stat-total">{{ store.total.toLocaleString() }}</span>
          <span class="stat-label">条结果</span>
          <span class="stat-time">{{ store.response.query_time_ms }}ms</span>
        </template>
      </div>
    </div>

    <div v-if="store.loading && !store.items.length" class="grid loading-grid">
      <div v-for="i in 12" :key="i" class="skeleton-card">
        <div class="skeleton-thumb" />
        <div class="skeleton-body">
          <div class="skeleton-line w60" />
          <div class="skeleton-line w40" />
        </div>
      </div>
    </div>

    <div v-else-if="store.items.length" class="grid">
      <AssetCard
        v-for="item in visibleItems"
        :key="item.id"
        :item="item"
      />
    </div>

    <div v-else class="empty-state" :class="{ 'is-search-empty': hasActiveSearch }">
      <div class="empty-visual" aria-hidden="true">
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
          <rect x="13" y="14" width="34" height="34" rx="8" fill="currentColor" opacity="0.08" />
          <path d="M29 22h13M22 31h20M22 40h12" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.58" />
          <circle cx="43" cy="43" r="12" fill="var(--bg-panel)" stroke="currentColor" stroke-width="2" />
          <path d="m52 52 7 7" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
          <path d="M38 43h10" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </div>

      <div class="empty-copy">
        <div class="empty-kicker">{{ moduleLabel }}资源</div>
        <h3>{{ emptyTitle }}</h3>
        <p>{{ emptyDescription }}</p>
      </div>

      <div v-if="emptyChips.length" class="empty-chips">
        <span
          v-for="chip in emptyChips"
          :key="chip.id"
          class="empty-chip"
          :class="`empty-chip--${chip.tone}`"
        >
          <span class="empty-chip-label">{{ chip.label }}</span>
          <span class="empty-chip-value">{{ chip.value }}</span>
        </span>
      </div>

      <div v-if="hasActiveSearch" class="empty-actions">
        <button type="button" class="empty-action is-primary" @click="clearSearchContext">
          清空条件
        </button>
        <button
          v-if="store.query"
          type="button"
          class="empty-action"
          @click="clearQueryOnly"
        >
          只清空搜索词
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-grid {
  min-height: 0;
}

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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}

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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  padding: 56px 24px 64px;
  gap: 16px;
  text-align: center;
  color: var(--text-muted);
}

.empty-state.is-search-empty {
  min-height: 420px;
}

.empty-visual {
  display: grid;
  place-items: center;
  color: var(--accent);
  filter: drop-shadow(0 10px 24px rgba(45, 212, 191, 0.08));
}

.empty-copy {
  max-width: 620px;
}

.empty-kicker {
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  color: var(--accent-text);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.empty-copy h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 750;
  line-height: 1.25;
  color: var(--text-primary);
}

.empty-copy p {
  margin: 10px auto 0;
  max-width: 560px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.empty-chips {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 760px;
}

.empty-chip {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 260px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.28);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 28px;
  overflow: hidden;
}

.empty-chip-label {
  flex: 0 0 auto;
  padding: 0 8px;
  border-right: 1px solid var(--border-subtle);
  color: var(--text-muted);
}

.empty-chip-value {
  min-width: 0;
  padding: 0 9px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}

.empty-chip--query {
  border-color: rgba(45, 212, 191, 0.28);
}

.empty-chip--match {
  border-color: rgba(34, 197, 94, 0.26);
}

.empty-chip--exclude {
  border-color: rgba(239, 68, 68, 0.28);
}

.empty-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 2px;
}

.empty-action {
  height: 34px;
  padding: 0 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.empty-action:hover {
  border-color: var(--border-light);
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.empty-action.is-primary {
  border-color: var(--border-accent);
  background: var(--accent);
  color: var(--accent-text);
}

.empty-action.is-primary:hover {
  filter: brightness(1.08);
}

@media (max-width: 720px) {
  .grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }

  .empty-state {
    min-height: 320px;
    padding: 42px 14px 48px;
  }

  .empty-copy h3 {
    font-size: 18px;
  }

  .empty-copy p {
    font-size: 12px;
  }

  .empty-chip {
    max-width: 100%;
  }
}
</style>
