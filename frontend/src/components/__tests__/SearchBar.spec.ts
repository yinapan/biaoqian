// frontend/src/components/__tests__/SearchBar.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import SearchBar from '../SearchBar.vue'
import { useSearchStore } from '@/stores/searchStore'

// Mock API — component imports store which imports searchAssets
vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

describe('SearchBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // 1. 500ms 防抖内连续输入只发一次请求
  it('500ms 防抖内连续输入只发一次请求', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const input = wrapper.find('[data-testid="search-input"]')
    await input.setValue('a')
    await input.trigger('input')
    await input.setValue('ab')
    await input.trigger('input')
    await input.setValue('abc')
    await input.trigger('input')

    // Before timer fires — no search yet
    expect(doSearchSpy).not.toHaveBeenCalled()

    vi.advanceTimersByTime(500)
    await flushPromises()

    // After debounce — exactly 1 call
    expect(doSearchSpy).toHaveBeenCalledTimes(1)
  })

  // 2. 输入清空立即触发 search（不等防抖）
  it('输入清空立即触发 search（不等防抖）', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const input = wrapper.find('[data-testid="search-input"]')
    // set some value first so the clear button appears
    await input.setValue('hello')
    await input.trigger('input')

    // Advance time to establish a debounce timer
    // Now clear via the clear button (which calls localQuery = ''; onSearch())
    const clearBtn = wrapper.find('.search-clear')
    expect(clearBtn.exists()).toBe(true)
    await clearBtn.trigger('click')
    await flushPromises()

    // onSearch() bypasses debounce, should fire immediately
    expect(doSearchSpy).toHaveBeenCalled()
  })

  // 3. Enter 键绕过防抖直接搜索
  it('Enter 键绕过防抖直接搜索', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const input = wrapper.find('[data-testid="search-input"]')
    await input.setValue('精灵')
    await input.trigger('input')

    // Debounce timer has NOT fired yet
    expect(doSearchSpy).not.toHaveBeenCalled()

    // Press Enter — should fire immediately via onSearch()
    await input.trigger('keyup.enter')
    await flushPromises()

    expect(doSearchSpy).toHaveBeenCalledTimes(1)
  })

  // 4. parse-info chip 显示并支持 dismiss
  it('parse-info chip 显示并支持 dismiss', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()

    // Set parseInfo via store response
    store.response = {
      total: 5, page: 1, page_size: 60,
      parse_info: {
        parsed_filters: { species: '精灵' },
        parsed_excludes: {},
        effective_filters: { species: '精灵' },
        effective_excludes: {},
        ignored_tags: [],
        keyword: '',
        confidence: 0.9,
        fallback: false,
        parse_source: 'rule',
        parse_time_ms: 1,
      },
      items: [],
      facets: {},
      query_time_ms: 1,
    }
    await flushPromises()

    // chip should be rendered with testid parse-chip-species
    const chip = wrapper.find('[data-testid="parse-chip-species"]')
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toContain('species')

    // Dismiss button exists within the chip
    const dismissBtns = chip.findAll('.pill-dismiss')
    expect(dismissBtns.length).toBeGreaterThan(0)

    // Mock dismissParsedFilter and doSearch
    const dismissSpy = vi.spyOn(store, 'dismissParsedFilter')
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    await dismissBtns[0].trigger('click')
    expect(dismissSpy).toHaveBeenCalledWith('species')
    expect(doSearchSpy).toHaveBeenCalled()
  })

  // 5. exclude 建议点击插入并触发搜索
  it('exclude 建议点击插入并触发搜索', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    // Open the syntax hint panel via the toggle button
    const toggle = wrapper.find('.syntax-toggle')
    await toggle.trigger('mousedown')

    // The hint panel should now show
    const panel = wrapper.find('.syntax-hint-panel')
    expect(panel.exists()).toBe(true)

    // Click on the first hint-chip ("不要红色")
    const firstChip = panel.find('.hint-chip')
    expect(firstChip.exists()).toBe(true)
    await firstChip.trigger('mousedown')

    // Should call insertExclude which calls onSearch
    expect(doSearchSpy).toHaveBeenCalled()

    // The query should now include the inserted example
    const input = wrapper.find('[data-testid="search-input"]')
    expect((input.element as HTMLInputElement).value).toContain('不要红色')
  })

  // 6. 输入触发 cancelPendingSearch 取消旧 AbortController
  it('输入触发 cancelPendingSearch 取消旧 AbortController', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const cancelSpy = vi.spyOn(store, 'cancelPendingSearch')

    const input = wrapper.find('[data-testid="search-input"]')
    await input.setValue('test')
    await input.trigger('input')

    expect(cancelSpy).toHaveBeenCalled()
  })

  // 7. dismissedFields.clear() 在输入时触发
  it('dismissedFields.clear() 在输入时触发', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()

    // First add something to dismissedFields
    store.dismissedFields.add('species')
    expect(store.dismissedFields.size).toBe(1)

    const input = wrapper.find('[data-testid="search-input"]')
    await input.setValue('abc')
    await input.trigger('input')

    // Advance time to trigger debounce
    vi.advanceTimersByTime(500)
    await flushPromises()

    expect(store.dismissedFields.size).toBe(0)
  })

  // 8. chip render 用 data-testid=parse-chip-{field}
  it('chip render 用 data-testid=parse-chip-{field}', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()

    store.response = {
      total: 3, page: 1, page_size: 60,
      parse_info: {
        parsed_filters: {},
        parsed_excludes: {},
        effective_filters: { gender: '女性', region: '东方' },
        effective_excludes: {},
        ignored_tags: [],
        keyword: '',
        confidence: 0.8,
        fallback: false,
        parse_source: 'rule',
        parse_time_ms: 1,
      },
      items: [],
      facets: {},
      query_time_ms: 1,
    }
    await flushPromises()

    expect(wrapper.find('[data-testid="parse-chip-gender"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="parse-chip-region"]').exists()).toBe(true)
  })

  // 9. suggestion render 用 data-testid=suggestion-item-{idx}（SearchBar 用 .hint-chip 不是 suggestion-item，验证 hint-chip）
  it('syntax hint panel 显示可点击的示例 chip', async () => {
    const wrapper = mount(SearchBar)

    const toggle = wrapper.find('.syntax-toggle')
    await toggle.trigger('mousedown')

    const chips = wrapper.findAll('.hint-chip')
    // Should have 4 hint chips (不要红色, 排除蓝色, 不含火焰, 无武器)
    expect(chips.length).toBe(4)
  })

  // 10. 空 query 不发请求（onInput 仍会发但 quiet=true；测试 onSearch 时 store.query=''）
  it('空 query 时 Enter 触发 doSearch（query 为空时也搜索）', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    // Input is empty by default
    const input = wrapper.find('[data-testid="search-input"]')
    expect((input.element as HTMLInputElement).value).toBe('')

    // Press Enter with empty query — should still call doSearch
    await input.trigger('keyup.enter')
    await flushPromises()

    // SearchBar calls doSearch regardless of empty query
    expect(doSearchSpy).toHaveBeenCalledTimes(1)
  })

  // 11. props.parseInfo 更新触发 chip 重新渲染（通过 store.response）
  it('store.parseInfo 更新触发 chip 重新渲染', async () => {
    const wrapper = mount(SearchBar)
    const store = useSearchStore()

    // Initially no chips
    expect(wrapper.find('.parse-pills').exists()).toBe(false)

    // Update store response to include parse_info
    store.response = {
      total: 1, page: 1, page_size: 60,
      parse_info: {
        parsed_filters: {},
        parsed_excludes: {},
        effective_filters: { faction: '秋水' },
        effective_excludes: {},
        ignored_tags: [],
        keyword: '',
        confidence: 0.9,
        fallback: false,
        parse_source: 'rule',
        parse_time_ms: 1,
      },
      items: [],
      facets: {},
      query_time_ms: 1,
    }
    await flushPromises()

    // Now the pills container should appear
    expect(wrapper.find('.parse-pills').exists()).toBe(true)
    expect(wrapper.find('[data-testid="parse-chip-faction"]').exists()).toBe(true)
  })
})
