import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchAssets, getTagDefinitions } from '@/api/search'
import type { SearchResponse, TagDefinition } from '@/types'

interface SearchOptions {
  quiet?: boolean
}

export const useSearchStore = defineStore('search', () => {
  // ---- state ----
  const moduleType = ref(1)
  const query = ref('')
  const filters = ref<Record<string, any>>({})
  const dismissedFields = ref<Set<string>>(new Set())
  const page = ref(1)
  const pageSize = ref(60)
  const loading = ref(false)

  const response = ref<SearchResponse | null>(null)
  const tagDefinitions = ref<TagDefinition[]>([])
  let latestSearchId = 0
  let currentSearchController: AbortController | null = null

  // ---- getters ----
  const items = computed(() => response.value?.items ?? [])
  const total = computed(() => response.value?.total ?? 0)
  const parseInfo = computed(() => response.value?.parse_info ?? null)
  const facets = computed(() => response.value?.facets ?? {})

  // ---- actions ----
  async function doSearch(options?: SearchOptions) {
    const searchId = ++latestSearchId
    currentSearchController?.abort()
    const controller = new AbortController()
    currentSearchController = controller
    if (!options?.quiet) {
      loading.value = true
    }
    try {
      const result = await searchAssets({
        module_type: moduleType.value,
        query: query.value || undefined,
        filters: Object.keys(filters.value).length
          ? filters.value
          : undefined,
        dismissed_fields: dismissedFields.value.size
          ? [...dismissedFields.value]
          : undefined,
        page: page.value,
        page_size: pageSize.value,
      }, controller.signal)
      if (searchId === latestSearchId) {
        response.value = result
      }
    } catch (error) {
      if (controller.signal.aborted) {
        return
      }
      throw error
    } finally {
      if (currentSearchController === controller) {
        currentSearchController = null
      }
      if (searchId === latestSearchId) {
        loading.value = false
      }
    }
  }

  async function loadDefinitions() {
    tagDefinitions.value = await getTagDefinitions(moduleType.value)
  }

  function setModuleType(mod: number) {
    moduleType.value = mod
    filters.value = {}
    dismissedFields.value = new Set()
    query.value = ''
    page.value = 1
    response.value = null
  }

  function setFilter(field: string, value: any) {
    if (
      value === null ||
      value === undefined ||
      (Array.isArray(value) && !value.length)
    ) {
      delete filters.value[field]
    } else {
      filters.value[field] = value
    }
    page.value = 1
  }

  function setPage(p: number) {
    page.value = p
  }

  function clearFilters() {
    filters.value = {}
    dismissedFields.value = new Set()
    page.value = 1
  }

  function dismissParsedFilter(field: string) {
    dismissedFields.value.add(field)
    page.value = 1
  }

  return {
    // state
    moduleType,
    query,
    filters,
    dismissedFields,
    page,
    pageSize,
    loading,
    response,
    tagDefinitions,
    // getters
    items,
    total,
    parseInfo,
    facets,
    // actions
    doSearch,
    loadDefinitions,
    setModuleType,
    setFilter,
    setPage,
    clearFilters,
    dismissParsedFilter,
  }
})
