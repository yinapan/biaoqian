<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
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

function onInput(val: string) {
  localQuery.value = val
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
  <div class="search-bar-wrapper">
    <el-input
      v-model="localQuery"
      placeholder="输入自然语言搜索，例如：写实风格的女性角色"
      size="large"
      clearable
      :prefix-icon="Search"
      @input="onInput"
      @keyup.enter="onSearch"
      @clear="onSearch"
    />

    <!-- Parsed tags display -->
    <div v-if="store.parseInfo" class="parse-info">
      <el-tag
        v-for="[field, value] in filterEntries(store.parseInfo)"
        :key="field"
        type="success"
        size="small"
        class="parse-tag"
      >
        {{ field }}: {{ Array.isArray(value) ? value.join(', ') : value }}
      </el-tag>

      <el-tag
        v-if="store.parseInfo.keyword"
        size="small"
        class="parse-tag"
      >
        关键词: {{ store.parseInfo.keyword }}
      </el-tag>

      <el-tag
        v-for="ignored in store.parseInfo.ignored_tags"
        :key="ignored.field + ignored.value"
        type="info"
        size="small"
        class="parse-tag"
        effect="plain"
      >
        <s>{{ ignored.field }}: {{ ignored.value }}</s>
        ({{ ignored.reason }})
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.search-bar-wrapper {
  max-width: 720px;
}

.parse-info {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.parse-tag {
  border-radius: 4px;
}
</style>
