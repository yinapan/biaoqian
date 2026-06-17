<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { TagDefinition } from '@/types'

const props = defineProps<{
  definition: TagDefinition
}>()

const store = useSearchStore()
const collapsed = ref(false)
const searchText = ref('')

const filteredValues = computed(() => {
  const vals = props.definition.values
  if (!vals || !searchText.value) return vals
  const q = searchText.value.toLowerCase()
  return vals.filter(
    (v) => (v.display_name || v.value).toLowerCase().includes(q),
  )
})

const field = computed(() => props.definition.field_name)

const selected = computed({
  get: () => store.filters[field.value] ?? (isMulti.value ? [] : null),
  set: (val: any) => {
    store.setFilter(field.value, val)
    store.doSearch()
  },
})

const isMulti = computed(() =>
  ['enum_single', 'enum_multi'].includes(props.definition.field_type),
)
const isRange = computed(() => props.definition.field_type === 'number_range')
const isBool = computed(() => props.definition.field_type === 'boolean')
const isText = computed(() => props.definition.field_type === 'text')

const rangeMin = computed(() => props.definition.config?.min ?? 0)
const rangeMax = computed(() => props.definition.config?.max ?? 100)
const rangeStep = computed(() => props.definition.config?.step ?? 1)

const rangeValue = computed({
  get: () => {
    const v = store.filters[field.value]
    if (Array.isArray(v) && v.length === 2) return v as [number, number]
    return [rangeMin.value, rangeMax.value] as [number, number]
  },
  set: (val: [number, number]) => {
    if (val[0] === rangeMin.value && val[1] === rangeMax.value) {
      store.setFilter(field.value, null)
    } else {
      store.setFilter(field.value, val)
    }
    store.doSearch()
  },
})

const boolValue = computed({
  get: () => {
    const v = store.filters[field.value]
    return v === true
  },
  set: (val: boolean) => {
    store.setFilter(field.value, val || null)
    store.doSearch()
  },
})

const activeCount = computed(() => {
  if (isMulti.value) {
    const v = store.filters[field.value]
    return Array.isArray(v) ? v.length : 0
  }
  return store.filters[field.value] != null ? 1 : 0
})

const hasMany = computed(
  () => props.definition.values && props.definition.values.length > 8,
)

function toggleOption(val: string) {
  const current = Array.isArray(selected.value) ? [...selected.value] : []
  const idx = current.indexOf(val)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(val)
  }
  selected.value = current
}

function isSelected(val: string) {
  return Array.isArray(selected.value) && selected.value.includes(val)
}
</script>

<template>
  <div v-if="!isText" class="filter-group" :class="{ collapsed, 'has-active': activeCount > 0 }">
    <!-- Group header -->
    <button class="group-header" @click="collapsed = !collapsed">
      <span class="header-label">{{ definition.display_name }}</span>
      <span class="header-right">
        <span v-if="activeCount > 0" class="active-badge">{{ activeCount }}</span>
        <span class="chevron-icon" :class="{ rotated: collapsed }">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2.5 3.5L5 6L7.5 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
      </span>
    </button>

    <!-- Group body -->
    <div v-show="!collapsed" class="group-body">
      <!-- Enum: tag-pill selection -->
      <template v-if="isMulti">
        <!-- Search input for large groups -->
        <div v-if="hasMany" class="search-wrap">
          <svg class="search-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="searchText"
            class="search-input"
            :placeholder="`在 ${definition.display_name} 中搜索…`"
          />
          <span v-if="searchText" class="search-count">{{ filteredValues?.length ?? 0 }}</span>
        </div>

        <!-- Tag pills area -->
        <div class="pills-scroll" :class="{ tall: hasMany }">
          <div class="tag-pills">
            <button
              v-for="opt in filteredValues"
              :key="opt.value"
              class="tag-pill"
              :class="{ active: isSelected(opt.value) }"
              @click="toggleOption(opt.value)"
            >
              <span class="pill-dot" v-if="isSelected(opt.value)"></span>
              {{ opt.display_name || opt.value }}
            </button>
          </div>
          <span v-if="filteredValues && filteredValues.length === 0" class="no-match">
            无匹配项
          </span>
        </div>
      </template>

      <!-- Number range slider -->
      <div v-else-if="isRange" class="range-wrap">
        <el-slider
          v-model="rangeValue"
          range
          :min="rangeMin"
          :max="rangeMax"
          :step="rangeStep"
        />
      </div>

      <!-- Boolean switch -->
      <div v-else-if="isBool" class="bool-wrap">
        <el-switch v-model="boolValue" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-group {
  margin-bottom: 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
  animation: groupReveal 0.3s ease both;
  transition: border-color 0.2s ease;
}

.filter-group:hover {
  border-color: var(--border-light);
}

.filter-group.has-active {
  border-color: rgba(232, 168, 56, 0.15);
  background: linear-gradient(
    180deg,
    rgba(232, 168, 56, 0.03) 0%,
    var(--bg-surface) 100%
  );
}

.filter-group.collapsed {
  background: transparent;
  border-color: var(--border-subtle);
}

.filter-group.collapsed:hover {
  background: var(--bg-surface);
}

@keyframes groupReveal {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* --- Header --- */
.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: none;
  cursor: pointer;
  transition: background 0.15s ease;
}

.group-header:hover {
  background: var(--bg-surface-hover);
}

.header-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  transition: color 0.15s ease;
}

.filter-group.has-active .header-label {
  color: var(--text-primary);
}

.group-header:hover .header-label {
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.active-badge {
  font-size: 10px;
  font-weight: 700;
  font-family: var(--font-mono);
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 4px;
  background: var(--accent);
  color: var(--text-on-accent);
}

.chevron-icon {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  transition: transform 0.2s ease;
}

.chevron-icon.rotated {
  transform: rotate(-90deg);
}

/* --- Group body --- */
.group-body {
  padding: 0 12px 10px;
}

/* --- Search input --- */
.search-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-root);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 0 8px;
  margin-bottom: 8px;
  transition: border-color 0.15s ease;
}

.search-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-wrap:focus-within .search-icon {
  color: var(--accent);
}

.search-input {
  flex: 1;
  padding: 6px 0;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 12px;
  outline: none;
  min-width: 0;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-count {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  background: var(--bg-surface-hover);
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

/* --- Pills scroll area --- */
.pills-scroll {
  max-height: 140px;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

.pills-scroll.tall {
  max-height: 200px;
}

.pills-scroll::-webkit-scrollbar {
  width: 3px;
}

.pills-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
}

.pills-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* --- Tag pills --- */
.tag-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: var(--bg-root);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 11.5px;
  cursor: pointer;
  transition: all 0.12s ease;
  white-space: nowrap;
  line-height: 1.5;
}

.tag-pill:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
  border-color: var(--border-light);
}

.tag-pill.active {
  background: var(--accent-soft);
  border-color: rgba(232, 168, 56, 0.25);
  color: var(--accent-text);
}

.tag-pill.active:hover {
  background: rgba(232, 168, 56, 0.18);
  border-color: rgba(232, 168, 56, 0.4);
}

.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.no-match {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 2px;
  display: block;
}

/* --- Range / Bool wrappers --- */
.range-wrap {
  padding: 4px 4px 0;
}

.bool-wrap {
  padding: 2px 0;
}
</style>
