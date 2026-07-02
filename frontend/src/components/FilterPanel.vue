<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import FilterGroup from './FilterGroup.vue'

const store = useSearchStore()
const INITIAL_GROUP_RENDER_LIMIT = 6
const GROUP_RENDER_BATCH_SIZE = 4
const groupRenderLimit = ref(INITIAL_GROUP_RENDER_LIMIT)
let frameId: number | null = null

const filterableDefs = computed(() =>
  [...store.tagDefinitions.filter((d) => d.is_filterable)]
    .sort((a, b) => filterDisplayPriority(a) - filterDisplayPriority(b)),
)

function filterDisplayPriority(def: { field_name: string; sort_order: number }) {
  if (def.field_name === 'file_type') return -900
  return def.sort_order
}

/** Group consecutive definitions that share the same config.group into one entry */
const groupedDefs = computed(() => {
  const defs = filterableDefs.value
  const result: Array<{ key: string; group?: string; items: typeof defs }> = []
  for (const d of defs) {
    const grp = (d.config as any)?.group as string | undefined
    if (grp) {
      const last = result[result.length - 1]
      if (last && last.group === grp) {
        last.items.push(d)
        continue
      }
      result.push({ key: `grp-${grp}`, group: grp, items: [d] })
    } else {
      result.push({ key: d.field_name, items: [d] })
    }
  }
  return result
})

const visibleGroupedDefs = computed(() =>
  groupedDefs.value.slice(0, groupRenderLimit.value),
)

const activeFilterCount = computed(() => {
  let count = 0
  for (const key in store.filters) {
    const v = store.filters[key]
    if (v == null) continue
    if (Array.isArray(v)) count += v.length
    else count++
  }
  return count
})

function clearAll() {
  store.clearFilters()
  store.doSearch()
}

function cancelScheduledRender() {
  if (frameId !== null) {
    cancelAnimationFrame(frameId)
    frameId = null
  }
}

function scheduleNextRenderBatch(total: number) {
  if (groupRenderLimit.value >= total) {
    frameId = null
    return
  }

  frameId = requestAnimationFrame(() => {
    groupRenderLimit.value = Math.min(
      groupRenderLimit.value + GROUP_RENDER_BATCH_SIZE,
      total,
    )
    scheduleNextRenderBatch(total)
  })
}

watch(
  groupedDefs,
  async (defs) => {
    cancelScheduledRender()
    groupRenderLimit.value = Math.min(INITIAL_GROUP_RENDER_LIMIT, defs.length)
    await nextTick()
    scheduleNextRenderBatch(defs.length)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  cancelScheduledRender()
})
</script>

<template>
  <div class="filter-panel">
    <!-- Panel header -->
    <div class="panel-header">
      <div class="header-left">
        <span class="header-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
          </svg>
        </span>
        <span class="header-title">筛选</span>
        <span class="header-dim">{{ filterableDefs.length }}</span>
      </div>
      <button
        v-if="activeFilterCount > 0"
        class="clear-btn"
        data-testid="filter-clear-all"
        @click="clearAll"
      >
        清除 {{ activeFilterCount }}
      </button>
    </div>

    <!-- Filter groups -->
    <div class="panel-scroll">
      <template v-if="groupedDefs.length">
        <template v-for="(entry, idx) in visibleGroupedDefs" :key="entry.key">
          <!-- Grouped filters (e.g. 尺寸, 相机参数) -->
          <FilterGroup
            v-if="entry.group"
            :definition="entry.items[0]"
            :grouped-definitions="entry.items"
            :group-label="entry.group"
            :data-testid="`filter-group-${entry.key}`"
            :style="{ animationDelay: `${idx * 30}ms` }"
          />
          <!-- Single filter -->
          <FilterGroup
            v-else
            :definition="entry.items[0]"
            :data-testid="`filter-group-${entry.key}`"
            :style="{ animationDelay: `${idx * 30}ms` }"
          />
        </template>
      </template>
      <div v-else class="panel-empty">
        <span class="empty-icon">◇</span>
        <span class="empty-text">暂无筛选维度</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 14px;
  box-shadow: var(--shadow-card);
}

/* --- Header --- */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 14px;
  margin-bottom: 4px;
  position: relative;
}

.panel-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--border-subtle);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  color: var(--accent);
  display: flex;
  align-items: center;
  opacity: 0.8;
}

.header-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
  color: var(--text-primary);
}

.header-dim {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  background: var(--bg-surface);
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-subtle);
}

.clear-btn {
  font-size: 11px;
  font-family: var(--font-sans);
  color: var(--accent-text);
  background: var(--accent-soft);
  border: 1px solid var(--border-accent);
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.clear-btn:hover {
  background: rgba(196, 154, 92, 0.15);
}

/* --- Scroll area --- */
.panel-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0 0;
}

/* --- Empty state --- */
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 24px;
  opacity: 0.3;
}

.empty-text {
  font-size: 13px;
}
</style>
