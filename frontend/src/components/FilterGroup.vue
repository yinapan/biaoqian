<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { TagDefinition } from '@/types'

const props = defineProps<{
  definition: TagDefinition
  groupedDefinitions?: TagDefinition[]
  groupLabel?: string
}>()

const store = useSearchStore()
const collapsed = ref(false)
const searchText = ref('')
const textInput = ref('')
let textTimer: ReturnType<typeof setTimeout> | null = null

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

const facetMap = computed(() => {
  const buckets = store.facets[field.value] ?? []
  const map: Record<string, number> = {}
  for (const b of buckets) map[b.value] = b.count
  return map
})

function getFacetCount(val: string): number | null {
  const buckets = store.facets[field.value]
  if (!buckets || !buckets.length) return null
  return facetMap.value[val] ?? 0
}

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

function onTextInput() {
  if (textTimer) clearTimeout(textTimer)
  textTimer = setTimeout(() => {
    store.setFilter(field.value, textInput.value || null)
    store.doSearch()
  }, 500)
}

function clearTextFilter() {
  textInput.value = ''
  store.setFilter(field.value, null)
  store.doSearch()
}

const isGrouped = computed(() => !!props.groupedDefinitions && props.groupedDefinitions.length > 1)

const displayLabel = computed(() => props.groupLabel || props.definition.display_name)

const groupActiveCount = computed(() => {
  if (!isGrouped.value) return activeCount.value
  let count = 0
  for (const d of props.groupedDefinitions!) {
    if (store.filters[d.field_name] != null) count++
  }
  return count
})

function getGroupRangeValue(def: TagDefinition): [number, number] {
  const min = (def.config as any)?.min ?? 0
  const max = (def.config as any)?.max ?? 100
  const v = store.filters[def.field_name]
  if (Array.isArray(v) && v.length === 2) return v as [number, number]
  return [min, max]
}

function setGroupRangeValue(def: TagDefinition, val: [number, number]) {
  const min = (def.config as any)?.min ?? 0
  const max = (def.config as any)?.max ?? 100
  if (val[0] === min && val[1] === max) {
    store.setFilter(def.field_name, null)
  } else {
    store.setFilter(def.field_name, val)
  }
  store.doSearch()
}
</script>

<template>
  <div class="filter-group" :class="{ collapsed, 'has-active': groupActiveCount > 0 }">
    <!-- Group header -->
    <button class="group-header" @click="collapsed = !collapsed">
      <span class="header-label">{{ displayLabel }}</span>
      <span class="header-right">
        <span v-if="groupActiveCount > 0" class="active-badge">{{ groupActiveCount }}</span>
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
              <span v-if="getFacetCount(opt.value) !== null" class="pill-count">{{ getFacetCount(opt.value) }}</span>
            </button>
          </div>
          <span v-if="filteredValues && filteredValues.length === 0" class="no-match">
            无匹配项
          </span>
        </div>
      </template>

      <!-- Number range slider (grouped or single) -->
      <template v-else-if="isRange">
        <div v-if="isGrouped" class="grouped-ranges">
          <div v-for="gd in groupedDefinitions" :key="gd.field_name" class="grouped-range-item">
            <span class="range-label">{{ gd.display_name }}</span>
            <el-slider
              :model-value="getGroupRangeValue(gd)"
              @update:model-value="(v: any) => setGroupRangeValue(gd, v)"
              range
              :min="(gd.config as any)?.min ?? 0"
              :max="(gd.config as any)?.max ?? 100"
              :step="(gd.config as any)?.step ?? 1"
            />
          </div>
        </div>
        <div v-else class="range-wrap">
          <el-slider
            v-model="rangeValue"
            range
            :min="rangeMin"
            :max="rangeMax"
            :step="rangeStep"
          />
        </div>
      </template>

      <!-- Boolean switch -->
      <div v-else-if="isBool" class="bool-wrap">
        <el-switch v-model="boolValue" />
      </div>

      <!-- Text search input -->
      <div v-else-if="isText" class="text-filter-wrap">
        <div class="search-wrap">
          <svg class="search-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="textInput"
            class="search-input"
            :placeholder="`搜索${definition.display_name}…`"
            @input="onTextInput"
            @keyup.enter="onTextInput"
          />
          <button v-if="textInput" class="text-clear" @click="clearTextFilter">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-group {
  margin-bottom: 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.filter-group:hover {
  border-color: var(--border-light);
}

.filter-group.has-active {
  border-color: var(--border-accent);
}

.filter-group.collapsed {
  background: var(--bg-surface);
  border-color: var(--border-subtle);
}

.filter-group.collapsed:hover {
  background: var(--bg-surface);
}

/* --- Header --- */
.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 11px;
  border: none;
  background: none;
  cursor: pointer;
  transition: background 0.15s ease;
}

.group-header:hover {
  background: var(--bg-surface);
}

.header-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0;
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
  border-radius: 999px;
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
  padding: 0 11px 11px;
}

/* --- Search input --- */
.search-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 0 8px;
  margin-bottom: 8px;
  transition: border-color 0.15s ease;
}

.search-wrap:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
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
  padding: 4px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
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
  border-color: var(--border-accent);
  color: var(--accent-text);
}

.tag-pill.active:hover {
  background: rgba(196, 154, 92, 0.15);
}

.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.pill-count {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--text-muted);
  opacity: 0.7;
  margin-left: 2px;
}

.tag-pill.active .pill-count {
  color: var(--accent);
  opacity: 1;
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

.grouped-ranges {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.grouped-range-item {
  padding: 0 4px;
}

.range-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 2px;
  display: block;
}

.bool-wrap {
  padding: 2px 0;
}

.text-filter-wrap {
  padding: 0;
}

.text-clear {
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
}

.text-clear:hover {
  color: var(--accent);
}
</style>
