// frontend/src/stores/__tests__/searchStore.spec.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '../searchStore'

// Mock the API module — must be declared before any imports that pull it in
vi.mock('@/api/search', () => ({
  searchAssets: vi.fn(),
  getTagDefinitions: vi.fn(),
}))

import { searchAssets, getTagDefinitions } from '@/api/search'
import type { SearchResponse, TagDefinition } from '@/types'

// ---- helpers ----
function makeResponse(overrides: Partial<SearchResponse> = {}): SearchResponse {
  return {
    total: 0,
    page: 1,
    page_size: 60,
    parse_info: null,
    items: [],
    facets: {},
    query_time_ms: 1,
    ...overrides,
  }
}

function makeDef(fieldName = 'species'): TagDefinition {
  return {
    id: 1,
    field_name: fieldName,
    display_name: fieldName,
    field_type: 'enum',
    is_filterable: true,
    is_searchable: false,
    sort_order: 0,
    config: {},
    values: [],
  }
}

// ---- setup / teardown ----
beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(searchAssets).mockResolvedValue(makeResponse())
  vi.mocked(getTagDefinitions).mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ====================================================================
describe('searchStore', () => {

  // 1. setModuleType 重置 filters/query/page
  it('setModuleType 重置 filters/query/page', () => {
    const store = useSearchStore()
    store.query = 'elf'
    store.filters = { species: '精灵' }
    store.setFilter('species', '精灵')
    store.setPage(7)
    store.query = 'elf'

    store.setModuleType(3)

    expect(store.moduleType).toBe(3)
    expect(store.query).toBe('')
    expect(store.filters).toEqual({})
    expect(store.page).toBe(1)
  })

  // 2. setModuleType 同步置 loading=true 并清空 response（ffd4785）
  it('setModuleType 同步置 loading=true 并清空 response（ffd4785）', () => {
    const store = useSearchStore()
    store.response = makeResponse({ total: 99 })
    store.loading = false

    store.setModuleType(3)

    // Both must be synchronous — no await needed
    expect(store.loading).toBe(true)
    expect(store.response).toBeNull()
  })

  // 3. setModuleType 清空 dismissedFields 与 tagDefinitions
  it('setModuleType 清空 dismissedFields 与 tagDefinitions', () => {
    const store = useSearchStore()
    store.dismissParsedFilter('species')
    store.tagDefinitions = [makeDef()]

    store.setModuleType(2)

    expect(store.dismissedFields.size).toBe(0)
    expect(store.tagDefinitions).toEqual([])
  })

  // 4. setFilter 设置 enum_single 值并重置 page
  it('setFilter 设置 enum_single 值并重置 page', () => {
    const store = useSearchStore()
    store.setPage(5)

    store.setFilter('species', '人类')

    expect(store.filters['species']).toBe('人类')
    expect(store.page).toBe(1)
  })

  // 5. setFilter null 删除字段
  it('setFilter null 删除字段', () => {
    const store = useSearchStore()
    store.setFilter('species', '人类')
    expect(store.filters['species']).toBe('人类')

    store.setFilter('species', null)

    expect('species' in store.filters).toBe(false)
  })

  // 6. setFilter 空数组删除字段
  it('setFilter 空数组删除字段', () => {
    const store = useSearchStore()
    store.setFilter('region', ['东方'])
    expect(store.filters['region']).toEqual(['东方'])

    store.setFilter('region', [])

    expect('region' in store.filters).toBe(false)
  })

  // 7. doSearch 取消旧请求（AbortController）
  it('doSearch 取消旧请求（AbortController）', async () => {
    const store = useSearchStore()
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort')

    // Make first call hang so second call interrupts it
    let resolveFirst!: () => void
    vi.mocked(searchAssets).mockImplementationOnce(
      () => new Promise<SearchResponse>(res => { resolveFirst = () => res(makeResponse()) }),
    )

    const p1 = store.doSearch()
    const p2 = store.doSearch()   // should abort the first controller

    resolveFirst()
    await Promise.all([p1, p2])

    expect(abortSpy).toHaveBeenCalledTimes(1)
  })

  // 8. doSearch 旧响应被丢弃（latestSearchId 防竞态）
  it('doSearch 旧响应被丢弃（latestSearchId 防竞态）', async () => {
    const store = useSearchStore()

    const slowResp = makeResponse({ total: 1 })
    const fastResp = makeResponse({ total: 2 })

    let resolveFirst!: (r: SearchResponse) => void
    vi.mocked(searchAssets)
      .mockImplementationOnce(
        () => new Promise<SearchResponse>(res => { resolveFirst = res }),
      )
      .mockResolvedValueOnce(fastResp)

    const p1 = store.doSearch()
    const p2 = store.doSearch()   // second search finishes first

    await p2
    resolveFirst(slowResp)        // old slow response arrives late
    await p1

    // response should be from the second (fast) search
    expect(store.total).toBe(2)
  })

  // 9. doSearch quiet=true 不置 loading
  it('doSearch quiet=true 不置 loading', async () => {
    const store = useSearchStore()
    store.loading = false

    // Capture loading value *during* the await by checking before resolution
    let loadingDuringSearch = false
    vi.mocked(searchAssets).mockImplementationOnce(async () => {
      loadingDuringSearch = store.loading
      return makeResponse()
    })

    await store.doSearch({ quiet: true })

    expect(loadingDuringSearch).toBe(false)
    expect(store.loading).toBe(false)
  })

  // 10. doSearch quiet=false 置 loading=true
  it('doSearch quiet=false 置 loading=true', async () => {
    const store = useSearchStore()
    store.loading = false

    let loadingDuringSearch = false
    vi.mocked(searchAssets).mockImplementationOnce(async () => {
      loadingDuringSearch = store.loading
      return makeResponse()
    })

    await store.doSearch()

    expect(loadingDuringSearch).toBe(true)
    // After completion loading is reset to false
    expect(store.loading).toBe(false)
  })

  // 11. doSearch abort 不抛错（returns silently）
  it('doSearch abort 不抛错（returns silently）', async () => {
    const store = useSearchStore()

    vi.mocked(searchAssets).mockImplementationOnce((_req, signal) => {
      return new Promise<SearchResponse>((_res, rej) => {
        signal?.addEventListener('abort', () => {
          const err = new DOMException('Aborted', 'AbortError')
          rej(err)
        })
      })
    })

    const p = store.doSearch()
    store.cancelPendingSearch()

    // Must not throw — resolves silently
    await expect(p).resolves.toBeUndefined()
  })

  // 12. cancelPendingSearch 无 controller 时不报错
  it('cancelPendingSearch 无 controller 时不报错', () => {
    const store = useSearchStore()
    // No search in progress — should not throw
    expect(() => store.cancelPendingSearch()).not.toThrow()
  })

  // 13. loadDefinitions module_type 切换不赋值旧结果
  it('loadDefinitions module_type 切换不赋值旧结果', async () => {
    const store = useSearchStore()

    const defs = [makeDef('species')]
    let resolveFirst!: (d: TagDefinition[]) => void

    vi.mocked(getTagDefinitions)
      .mockImplementationOnce(
        () => new Promise<TagDefinition[]>(res => { resolveFirst = res }),
      )
      .mockResolvedValueOnce([])

    // Start load for module 1
    const p1 = store.loadDefinitions()

    // Switch to module 2 and load for module 2
    store.setModuleType(2)
    await store.loadDefinitions()

    // Now resolve the stale first call
    resolveFirst(defs)
    await p1

    // tagDefinitions should NOT be overwritten with module-1 defs
    expect(store.tagDefinitions).toEqual([])
  })

  // 14. setPage 更新页码
  it('setPage 更新页码', () => {
    const store = useSearchStore()
    store.setPage(5)
    expect(store.page).toBe(5)
  })

  // 15. clearFilters 清空 filters + dismissedFields + 重置 page
  it('clearFilters 清空 filters + dismissedFields + 重置 page', () => {
    const store = useSearchStore()
    store.setFilter('species', '精灵')
    store.dismissParsedFilter('region')
    store.setPage(7)

    store.clearFilters()

    expect(store.filters).toEqual({})
    expect(store.dismissedFields.size).toBe(0)
    expect(store.page).toBe(1)
  })

  // 16. dismissParsedFilter 添加到 dismissedFields 并重置 page
  it('dismissParsedFilter 添加到 dismissedFields 并重置 page', () => {
    const store = useSearchStore()
    store.setPage(4)

    store.dismissParsedFilter('species')

    expect(store.dismissedFields.has('species')).toBe(true)
    expect(store.page).toBe(1)
  })

  // 17. getters items/total/parseInfo/facets 默认值正确
  it('getters items/total/parseInfo/facets 默认值正确', () => {
    const store = useSearchStore()
    // Fresh store — response is null
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.parseInfo).toBeNull()
    expect(store.facets).toEqual({})
  })

})
