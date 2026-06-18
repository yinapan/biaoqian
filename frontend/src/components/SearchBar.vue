<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { ParseInfo } from '@/types'

const store = useSearchStore()

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const localQuery = ref(store.query)

watch(
  () => store.query,
  (v) => {
    localQuery.value = v
  },
)

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.query = localQuery.value
    store.page = 1
    store.doSearch()
  }, 300)
}

function onSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  store.query = localQuery.value
  store.page = 1
  store.doSearch()
}

function filterEntries(info: ParseInfo) {
  return Object.entries(info.effective_filters)
}
</script>

<template>
  <div class="search-wrapper">
    <div class="search-input-box">
      <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input
        v-model="localQuery"
        type="text"
        class="search-input"
        placeholder="搜索名称、标签或自然语言描述"
        @input="onInput"
        @keyup.enter="onSearch"
      />
      <button
        v-if="localQuery"
        class="search-clear"
        @click="localQuery = ''; onSearch()"
      >
        ×
      </button>
    </div>

    <!-- Parse info pills -->
    <div v-if="store.parseInfo" class="parse-pills">
      <span
        v-for="[field, value] in filterEntries(store.parseInfo)"
        :key="field"
        class="pill pill--match"
      >
        {{ field }}:
        {{ Array.isArray(value) ? value.join(', ') : value }}
      </span>

      <span
        v-if="store.parseInfo.keyword"
        class="pill pill--keyword"
      >
        关键词: {{ store.parseInfo.keyword }}
      </span>

      <span
        v-for="ignored in store.parseInfo.ignored_tags"
        :key="ignored.field + ignored.value"
        class="pill pill--ignored"
      >
        <s>{{ ignored.field }}: {{ ignored.value }}</s>
        <small>{{ ignored.reason }}</small>
      </span>
    </div>
  </div>
</template>

<style scoped>
.search-wrapper {
  width: 100%;
}

.search-input-box {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.search-icon {
  position: absolute;
  left: 14px;
  color: var(--text-muted);
  pointer-events: none;
  transition: color 0.2s;
}

.search-input-box:focus-within .search-icon {
  color: var(--accent);
}

.search-input {
  width: 100%;
  height: 44px;
  padding: 0 40px 0 42px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-input:hover {
  border-color: var(--border-light);
}

.search-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.search-clear {
  position: absolute;
  right: 8px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--bg-surface);
  color: var(--text-muted);
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  transition: all 0.15s;
}

.search-clear:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

/* --- Parse pills --- */
.parse-pills {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;
}

.pill--match {
  background: #eaf7ef;
  color: #1f6d3f;
  border: 1px solid #c9ead5;
}

.pill--keyword {
  background: var(--accent-soft);
  color: var(--accent-text);
  border: 1px solid var(--border-accent);
}

.pill--ignored {
  background: var(--bg-surface);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

.pill--ignored small {
  opacity: 0.6;
  font-size: 11px;
}
</style>
