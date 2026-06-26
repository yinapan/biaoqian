// frontend/src/components/__tests__/ModuleTabs.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import ModuleTabs from '../ModuleTabs.vue'
import { useSearchStore } from '@/stores/searchStore'

vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

describe('ModuleTabs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. 4 个 tab 切换
  it('4 个 tab 切换', async () => {
    const store = useSearchStore()
    const defSpy = vi.spyOn(store, 'loadDefinitions').mockResolvedValue()
    const searchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const wrapper = mount(ModuleTabs)

    // All 4 tabs should exist
    expect(wrapper.find('[data-testid="module-tab-1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="module-tab-2"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="module-tab-3"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="module-tab-4"]').exists()).toBe(true)

    // Click tab 2
    await wrapper.find('[data-testid="module-tab-2"]').trigger('click')
    await flushPromises()
    expect(store.moduleType).toBe(2)

    // Click tab 4
    await wrapper.find('[data-testid="module-tab-4"]').trigger('click')
    await flushPromises()
    expect(store.moduleType).toBe(4)
  })

  // 2. 当前 tab 高亮（active class）
  it('当前 tab 高亮', async () => {
    const store = useSearchStore()
    vi.spyOn(store, 'loadDefinitions').mockResolvedValue()
    vi.spyOn(store, 'doSearch').mockResolvedValue()

    const wrapper = mount(ModuleTabs)

    // Default moduleType is 1 → tab-1 should be active
    expect(wrapper.find('[data-testid="module-tab-1"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="module-tab-2"]').classes()).not.toContain('active')

    // Switch to tab 3
    await wrapper.find('[data-testid="module-tab-3"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="module-tab-3"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="module-tab-1"]').classes()).not.toContain('active')
  })

  // 3. 切换触发 reset（setModuleType 清空 filters/query/tagDefinitions）
  it('切换触发 reset', async () => {
    const store = useSearchStore()
    vi.spyOn(store, 'loadDefinitions').mockResolvedValue()
    vi.spyOn(store, 'doSearch').mockResolvedValue()

    // Set some state first
    store.setFilter('species', '精灵')
    store.query = 'test query'
    expect(store.filters['species']).toBe('精灵')

    const wrapper = mount(ModuleTabs)

    // Click a different tab
    await wrapper.find('[data-testid="module-tab-2"]').trigger('click')
    await flushPromises()

    // setModuleType should reset everything
    expect(store.filters).toEqual({})
    expect(store.query).toBe('')
    expect(store.page).toBe(1)
  })

  // 4. selectModule 用 Promise.all 并行 loadDefinitions + doSearch
  it('selectModule 用 Promise.all 并行 loadDefinitions + doSearch（ffd4785）', async () => {
    const store = useSearchStore()
    const defSpy = vi.spyOn(store, 'loadDefinitions').mockResolvedValue()
    const searchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const wrapper = mount(ModuleTabs)

    await wrapper.find('[data-testid="module-tab-2"]').trigger('click')
    await flushPromises()

    // Both should have been called (in parallel via Promise.all)
    expect(defSpy).toHaveBeenCalled()
    expect(searchSpy).toHaveBeenCalled()

    // They should be called after setModuleType (module should be 2)
    expect(store.moduleType).toBe(2)
  })
})
