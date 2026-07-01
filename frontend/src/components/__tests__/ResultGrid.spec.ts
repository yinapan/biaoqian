import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import ResultGrid from '../ResultGrid.vue'
import { useSearchStore } from '@/stores/searchStore'
import type { AssetItem } from '@/types'

vi.mock('../AssetCard.vue', () => ({
  default: {
    props: ['item'],
    template: '<article class="asset-card-stub" :data-id="item.id" />',
  },
}))

function makeItem(id: number): AssetItem {
  return {
    id,
    name: `asset-${id}`,
    resource_path: `asset-${id}.png`,
    thumbnail_path: `asset-${id}.png`,
    tags: {},
    relevance_score: 1,
    highlight: {},
  }
}

function setSearchResponse(items: AssetItem[]) {
  const store = useSearchStore()
  store.response = {
    total: items.length,
    page: 1,
    page_size: items.length,
    parse_info: null,
    items,
    facets: {},
    query_time_ms: 1,
  }
  return store
}

describe('ResultGrid', () => {
  let rafQueue: FrameRequestCallback[] = []

  beforeEach(() => {
    setActivePinia(createPinia())
    rafQueue = []
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      rafQueue.push(cb)
      return rafQueue.length
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('keeps fallback render batches for unknown modules', async () => {
    const items = Array.from({ length: 60 }, (_, index) => makeItem(index + 1))
    const store = setSearchResponse(items)
    store.moduleType = 99

    const wrapper = mount(ResultGrid)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(18)

    rafQueue.shift()?.(16)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(30)
  })

  it('limits the model module render batches to avoid flooding image previews', async () => {
    vi.useFakeTimers()
    const items = Array.from({ length: 60 }, (_, index) => makeItem(index + 1))
    const store = setSearchResponse(items)
    store.moduleType = 1

    const wrapper = mount(ResultGrid)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(8)

    vi.advanceTimersByTime(140)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(12)
  })

  it('limits the animator module render batches to avoid flooding GIF previews', async () => {
    vi.useFakeTimers()
    const items = Array.from({ length: 60 }, (_, index) => makeItem(index + 1))
    const store = setSearchResponse(items)
    store.moduleType = 3

    const wrapper = mount(ResultGrid)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(8)

    vi.advanceTimersByTime(140)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(12)
  })

  it('limits the effect module render batches because grid GIF previews can also flood loading', async () => {
    vi.useFakeTimers()
    const items = Array.from({ length: 60 }, (_, index) => makeItem(index + 1))
    const store = setSearchResponse(items)
    store.moduleType = 2

    const wrapper = mount(ResultGrid)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(8)

    vi.advanceTimersByTime(140)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(12)
  })

  it('limits the icon module render batches to avoid flooding image previews', async () => {
    vi.useFakeTimers()
    const items = Array.from({ length: 60 }, (_, index) => makeItem(index + 1))
    const store = setSearchResponse(items)
    store.moduleType = 4

    const wrapper = mount(ResultGrid)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(8)

    vi.advanceTimersByTime(140)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.asset-card-stub')).toHaveLength(12)
  })
})
