// frontend/src/components/__tests__/FilterGroup.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import FilterGroup from '../FilterGroup.vue'
import { useSearchStore } from '@/stores/searchStore'
import { slug } from '@/utils/testid'

vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

function makeEnumDef(
  fieldName: string,
  fieldType: 'enum_single' | 'enum_multi',
  values: { value: string; display_name: string }[],
) {
  return {
    id: 1,
    field_name: fieldName,
    display_name: fieldName,
    field_type: fieldType,
    is_filterable: true,
    is_searchable: false,
    sort_order: 0,
    config: {},
    values,
  }
}

describe('FilterGroup', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. enum_single 单选
  it('enum_single 单选', async () => {
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('species', 'enum_single', [
          { value: '人类', display_name: '人类' },
          { value: '精灵', display_name: '精灵' },
        ]),
      },
    })

    // Click one option
    const pills = wrapper.findAll('.tag-pill')
    expect(pills.length).toBe(2)

    await pills[0].trigger('click')
    await flushPromises()

    expect(store.filters['species']).toEqual(['人类'])
    expect(doSearchSpy).toHaveBeenCalled()
  })

  // 2. enum_multi 多选
  it('enum_multi 多选', async () => {
    const store = useSearchStore()
    const doSearchSpy = vi.spyOn(store, 'doSearch').mockResolvedValue()

    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('region', 'enum_multi', [
          { value: '东方', display_name: '东方' },
          { value: '西方', display_name: '西方' },
          { value: '南方', display_name: '南方' },
        ]),
      },
    })

    const pills = wrapper.findAll('.tag-pill')
    // Select two items
    await pills[0].trigger('click')
    await pills[1].trigger('click')
    await flushPromises()

    expect(store.filters['region']).toContain('东方')
    expect(store.filters['region']).toContain('西方')
    expect(store.filters['region'].length).toBe(2)
    expect(doSearchSpy).toHaveBeenCalledTimes(2)
  })

  // 3. number_range — slider rendered
  it('number_range renders el-slider', async () => {
    const wrapper = mount(FilterGroup, {
      props: {
        definition: {
          id: 2,
          field_name: 'height_cm',
          display_name: '高度',
          field_type: 'number_range',
          is_filterable: true,
          is_searchable: false,
          sort_order: 0,
          config: { min: 0, max: 300, step: 1 },
          values: [],
        },
      },
      global: {
        stubs: { 'el-slider': true },
      },
    })

    // The range wrapper should be present
    expect(wrapper.find('.range-wrap').exists()).toBe(true)
    // el-slider stub should be rendered
    expect(wrapper.find('el-slider-stub').exists()).toBe(true)
  })

  // 4. boolean 切换 — switch rendered
  it('boolean renders el-switch', async () => {
    const wrapper = mount(FilterGroup, {
      props: {
        definition: {
          id: 3,
          field_name: 'framed',
          display_name: '是否分帧',
          field_type: 'boolean',
          is_filterable: true,
          is_searchable: false,
          sort_order: 0,
          config: {},
          values: [],
        },
      },
      global: {
        stubs: { 'el-switch': true },
      },
    })

    expect(wrapper.find('.bool-wrap').exists()).toBe(true)
    expect(wrapper.find('el-switch-stub').exists()).toBe(true)
  })

  // 5. search-within 过滤大列表
  it('search-within 过滤大列表', async () => {
    // Items where display_name matches substring search pattern
    const values = [
      ...Array.from({ length: 15 }, (_, i) => ({ value: `red${i}`, display_name: `红色${i}` })),
      ...Array.from({ length: 5 }, (_, i) => ({ value: `blue${i}`, display_name: `蓝色${i}` })),
    ]
    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('semantic', 'enum_multi', values),
      },
    })

    // All 20 pills show initially (20 < RENDER_CAP)
    expect(wrapper.findAll('.tag-pill').length).toBe(20)

    // Search input should appear (20 > 8 hasMany)
    const searchInput = wrapper.find('.search-input')
    expect(searchInput.exists()).toBe(true)

    // Search for '蓝色' — only 5 pills should match (v-model filters display_name)
    await searchInput.setValue('蓝色')
    await flushPromises()

    const pills = wrapper.findAll('.tag-pill')
    expect(pills.length).toBe(5)
  })

  // 6. RENDER_CAP=200 无搜索时只渲染前 200 项
  it('RENDER_CAP=200 无搜索时只渲染前 200 项', () => {
    const fakeValues = Array.from({ length: 10838 }, (_, i) => ({
      value: `v${i}`, display_name: `V${i}`,
    }))
    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('semantic', 'enum_multi', fakeValues),
      },
    })

    expect(wrapper.findAll('.tag-pill').length).toBe(200)
  })

  // 7. 有搜索时渲染全部匹配项（不受 cap 限制）
  it('有搜索时渲染全部匹配项（不受 cap 限制）', async () => {
    const fakeValues = Array.from({ length: 10838 }, (_, i) => ({
      value: `v${i}`, display_name: `V${i}`,
    }))
    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('semantic', 'enum_multi', fakeValues),
      },
    })

    // Search for "v1" which matches v1, v10-v19, v100-v199, v1000-v1999, v10000-v10838 (thousands)
    const searchInput = wrapper.find('.search-input')
    await searchInput.setValue('v1')
    // Force the computed value to update via direct reactivity
    await flushPromises()

    const pills = wrapper.findAll('.tag-pill')
    // Should be many more than 200 (all matching)
    expect(pills.length).toBeGreaterThan(200)
  })

  // 8. cappedCount 提示条显示
  it('cappedCount 提示条显示总数', () => {
    const fakeValues = Array.from({ length: 10838 }, (_, i) => ({
      value: `v${i}`, display_name: `V${i}`,
    }))
    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('semantic', 'enum_multi', fakeValues),
      },
    })

    // cap-hint should be visible and show the total count (10838 raw, no comma)
    const hint = wrapper.find('.cap-hint')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('10838')
  })

  // 9. filter-option-{field}-{slug(value)} 钩子生成正确
  it('filter-option-{field}-{slug(value)} 钩子生成正确', () => {
    const values = [
      { value: '红色', display_name: '红色' },
      { value: 'Blue Sky', display_name: 'Blue Sky' },
    ]
    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('color', 'enum_multi', values),
      },
    })

    // testid for '红色' → slug('红色') = '红色' (already clean)
    const redPill = wrapper.find(`[data-testid="filter-option-color-${slug('红色')}"]`)
    expect(redPill.exists()).toBe(true)

    // testid for 'Blue Sky' → slug('Blue Sky') = 'blue-sky'
    const bluePill = wrapper.find(`[data-testid="filter-option-color-${slug('Blue Sky')}"]`)
    expect(bluePill.exists()).toBe(true)
  })
  it('shows zero facet counts when search returned no results and facet buckets are empty', () => {
    const store = useSearchStore()
    store.response = {
      total: 0,
      page: 1,
      page_size: 60,
      parse_info: null,
      items: [],
      facets: {},
      query_time_ms: 17,
    }

    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('resource_type', 'enum_multi', [
          { value: 'npc_source', display_name: 'npc_source' },
          { value: 'player', display_name: 'player' },
        ]),
      },
    })

    const pills = wrapper.findAll('.tag-pill')
    expect(pills).toHaveLength(2)
    expect(pills[0].text()).toContain('0')
    expect(pills[1].text()).toContain('0')
    expect(pills[0].classes()).toContain('is-zero')
    expect(pills[1].classes()).toContain('is-zero')
  })

  it('shows zero counts for fields missing from facets after a non-empty search response', () => {
    const store = useSearchStore()
    store.response = {
      total: 327,
      page: 1,
      page_size: 60,
      parse_info: null,
      items: [],
      facets: {
        file_type: [{ value: 'ani', count: 327 }],
      },
      query_time_ms: 55,
    }

    const wrapper = mount(FilterGroup, {
      props: {
        definition: makeEnumDef('resource_type', 'enum_multi', [
          { value: 'npc_source', display_name: 'npc_source' },
          { value: 'player', display_name: 'player' },
        ]),
      },
    })

    const pills = wrapper.findAll('.tag-pill')
    expect(pills[0].text()).toContain('0')
    expect(pills[1].text()).toContain('0')
    expect(pills[0].classes()).toContain('is-zero')
    expect(pills[1].classes()).toContain('is-zero')
  })
})
