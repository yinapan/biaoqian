// frontend/src/components/__tests__/FilterPanel.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import FilterPanel from '../FilterPanel.vue'
import { useSearchStore } from '@/stores/searchStore'

vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

function makeFilterableDef(i: number) {
  return {
    id: i,
    field_name: `f${i}`,
    display_name: `Field ${i}`,
    field_type: 'enum_single' as const,
    is_filterable: true,
    is_searchable: false,
    sort_order: i,
    config: {},
    values: [],
  }
}

describe('FilterPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. INITIAL_GROUP_RENDER_LIMIT=6 + rAF 批量挂载
  it('INITIAL_GROUP_RENDER_LIMIT=6 + rAF 批量挂载（791acb9）', async () => {
    const store = useSearchStore()
    store.tagDefinitions = Array.from({ length: 15 }, (_, i) => makeFilterableDef(i))

    const wrapper = mount(FilterPanel, {
      global: {
        stubs: { 'el-slider': true, 'el-switch': true },
      },
    })

    // Synchronously, only 6 groups should be rendered
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(6)

    // Each rAF adds a small batch so first open stays responsive.
    await new Promise<void>(r => requestAnimationFrame(() => r()))
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(10)

    await new Promise<void>(r => requestAnimationFrame(() => r()))
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(14)

    await new Promise<void>(r => requestAnimationFrame(() => r()))
    await nextTick()
    expect(wrapper.findAll('.filter-group').length).toBe(15)
  })

  // 2. 卸载时清理 rAF
  it('卸载时清理 rAF（791acb9）', async () => {
    const cancelSpy = vi.spyOn(globalThis, 'cancelAnimationFrame')

    const store = useSearchStore()
    store.tagDefinitions = Array.from({ length: 15 }, (_, i) => makeFilterableDef(i))

    const wrapper = mount(FilterPanel, {
      global: {
        stubs: { 'el-slider': true, 'el-switch': true },
      },
    })

    // Wait for the watch to fire and rAF to be scheduled
    await nextTick()

    // Unmount the component — should call cancelAnimationFrame
    wrapper.unmount()

    expect(cancelSpy).toHaveBeenCalled()
  })
  it('keeps file type near the top when definitions include file_type', async () => {
    const store = useSearchStore()
    store.tagDefinitions = [
      makeFilterableDef(1),
      makeFilterableDef(2),
      { ...makeFilterableDef(99), field_name: 'file_type', display_name: '文件类型', sort_order: 99 },
      makeFilterableDef(3),
    ]

    const wrapper = mount(FilterPanel, {
      global: {
        stubs: { 'el-slider': true, 'el-switch': true },
      },
    })

    await nextTick()

    const labels = wrapper.findAll('.filter-group .header-label').map((node) => node.text())
    expect(labels.slice(0, 2)).toContain('文件类型')
  })
})
