<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { ParseInfo } from '@/types'

const store = useSearchStore()

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const localQuery = ref(store.query)
const isFocused = ref(false)
const showSyntaxHint = ref(false)

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
    store.dismissedFields.clear()
    store.page = 1
    store.doSearch()
  }, 300)
}

function onSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  store.query = localQuery.value
  store.dismissedFields.clear()
  store.page = 1
  store.doSearch()
}

function dismissFilter(field: string) {
  store.dismissParsedFilter(field)
  store.doSearch()
}

function insertExclude(example: string) {
  localQuery.value = localQuery.value
    ? localQuery.value + ' ' + example
    : example
  showSyntaxHint.value = false
  onSearch()
}

function filterEntries(info: ParseInfo) {
  return Object.entries(info.effective_filters)
}

function excludeEntries(info: ParseInfo) {
  return Object.entries(info.effective_excludes || {})
}

function onBlur() {
  isFocused.value = false
  window.setTimeout(() => { showSyntaxHint.value = false }, 200)
}
</script>

<template>
  <div class="search-wrapper">
    <div class="search-input-box" :class="{ focused: isFocused }">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <circle cx="11" cy="11" r="7"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input
        v-model="localQuery"
        type="text"
        class="search-input"
        placeholder="搜索名称、标签，支持排除语法如 不要红色"
        @input="onInput"
        @keyup.enter="onSearch"
        @focus="isFocused = true"
        @blur="onBlur"
      />
      <button
        v-if="localQuery"
        class="search-clear"
        @click="localQuery = ''; onSearch()"
        title="清空"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <button
        class="syntax-toggle"
        :class="{ active: showSyntaxHint }"
        @mousedown.prevent="showSyntaxHint = !showSyntaxHint"
        title="搜索语法提示"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </button>
    </div>

    <!-- Syntax hint dropdown -->
    <Transition name="hint-fade">
      <div v-if="showSyntaxHint" class="syntax-hint-panel">
        <div class="hint-header">搜索语法</div>
        <div class="hint-section">
          <div class="hint-title">排除语法</div>
          <div class="hint-desc">在搜索词前加排除前缀，可过滤不想要的结果</div>
          <div class="hint-examples">
            <button class="hint-chip" @mousedown.prevent="insertExclude('不要红色')">
              <span class="chip-prefix">不要</span>红色
            </button>
            <button class="hint-chip" @mousedown.prevent="insertExclude('排除蓝色')">
              <span class="chip-prefix">排除</span>蓝色
            </button>
            <button class="hint-chip" @mousedown.prevent="insertExclude('不含火焰')">
              <span class="chip-prefix">不含</span>火焰
            </button>
            <button class="hint-chip" @mousedown.prevent="insertExclude('无武器')">
              <span class="chip-prefix">无</span>武器
            </button>
          </div>
        </div>
        <div class="hint-section">
          <div class="hint-title">支持的排除前缀</div>
          <div class="hint-prefixes">
            <code>不要</code>
            <code>不含</code>
            <code>排除</code>
            <code>去掉</code>
            <code>没有</code>
            <code>无</code>
            <code>非</code>
            <code>不是</code>
          </div>
        </div>
        <div class="hint-section">
          <div class="hint-title">组合示例</div>
          <div class="hint-desc">
            <code class="hint-example-full">红色 不要火焰 女性</code>
            <span class="hint-arrow">→</span>
            <span>搜索红色女性，排除火焰相关</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Parse info pills -->
    <div v-if="store.parseInfo" class="parse-pills">
      <span
        v-for="[field, value] in filterEntries(store.parseInfo)"
        :key="field"
        class="pill pill--match"
      >
        <svg class="pill-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
        <span class="pill-label">{{ field }}: {{ Array.isArray(value) ? value.join(', ') : value }}</span>
        <button class="pill-dismiss" @click="dismissFilter(field)" title="移除此标签">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/></svg>
        </button>
      </span>

      <span
        v-for="[field, value] in excludeEntries(store.parseInfo)"
        :key="'ex-' + field"
        class="pill pill--exclude"
      >
        <svg class="pill-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="9"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/>
        </svg>
        <span class="pill-label">{{ field }}: {{ Array.isArray(value) ? value.join(', ') : value }}</span>
        <button class="pill-dismiss" @click="dismissFilter(field)" title="取消排除">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/></svg>
        </button>
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
  position: relative;
}

.search-input-box {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.search-input-box.focused {
  box-shadow: 0 0 0 2px var(--accent-soft), var(--shadow-card);
}

.search-icon {
  position: absolute;
  left: 14px;
  color: var(--text-muted);
  pointer-events: none;
  transition: color 0.2s;
}

.search-input-box.focused .search-icon {
  color: var(--accent);
}

.search-input {
  width: 100%;
  height: 44px;
  padding: 0 76px 0 40px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  transition: all 0.2s ease;
}

.search-input::placeholder {
  color: var(--text-muted);
  font-size: 12.5px;
}

.search-input:hover {
  border-color: var(--border-light);
}

.search-input:focus {
  border-color: var(--accent);
}

.search-clear {
  position: absolute;
  right: 36px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--bg-surface);
  color: var(--text-muted);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.15s;
}

.search-clear:hover {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}

.syntax-toggle {
  position: absolute;
  right: 10px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.15s;
}

.syntax-toggle:hover,
.syntax-toggle.active {
  color: var(--accent);
  background: var(--accent-soft);
}

/* --- Syntax hint panel --- */
.syntax-hint-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  padding: 16px;
}

.hint-header {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.hint-section {
  margin-bottom: 14px;
}

.hint-section:last-child {
  margin-bottom: 0;
}

.hint-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.hint-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.hint-examples {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.hint-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-sans);
}

.hint-chip:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-text);
}

.chip-prefix {
  color: #f87171;
  font-weight: 600;
}

.hint-prefixes {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.hint-prefixes code {
  padding: 2px 8px;
  border-radius: 3px;
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
  font-size: 11px;
  font-family: var(--font-mono);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.hint-example-full {
  padding: 3px 8px;
  border-radius: 3px;
  background: var(--bg-surface);
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-primary);
}

.hint-arrow {
  color: var(--text-muted);
  font-size: 12px;
}

.hint-fade-enter-active,
.hint-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.hint-fade-enter-from,
.hint-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* --- Parse pills --- */
.parse-pills {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 50;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
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

.pill-icon {
  flex-shrink: 0;
}

.pill--match {
  background: rgba(34, 197, 94, 0.14);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.24);
}

.pill-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 2px;
  border: none;
  background: transparent;
  color: inherit;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.15s;
  padding: 0;
}

.pill-dismiss:hover {
  opacity: 1;
  background: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.pill--exclude {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.24);
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
