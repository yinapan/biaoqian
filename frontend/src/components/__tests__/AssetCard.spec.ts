// frontend/src/components/__tests__/AssetCard.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import AssetCard from '../AssetCard.vue'
import { useSearchStore } from '@/stores/searchStore'
import type { AssetItem } from '@/types'

vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

function makeItem(overrides: Partial<AssetItem> = {}): AssetItem {
  return {
    id: 1,
    name: 'test_asset',
    resource_path: '/path/to/asset',
    thumbnail_path: 'preview.png',
    tags: {},
    relevance_score: 0.9,
    highlight: {},
    ...overrides,
  }
}

describe('AssetCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. 预览图加载失败回退 SVG placeholder
  it('预览图加载失败回退 SVG placeholder 且实际渲染（@error 触发）', async () => {
    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ thumbnail_path: 'model_preview.png' }) },
      global: {
        stubs: { AssetDetailModal: true, 'el-dialog': true },
      },
    })

    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)

    // Trigger the @error event on the image
    await img.trigger('error')

    // After error, img src should be the SVG placeholder (starts with data:image/svg+xml)
    const src = (img.element as HTMLImageElement).src
    expect(src).toContain('data:image/svg+xml')
  })

  // 2. 模型模块预览 URL 正确（moduleType=1）
  it('模型模块预览 URL 正确', () => {
    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ thumbnail_path: 'hero_model.png' }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })

    const img = wrapper.find('img')
    expect((img.element as HTMLImageElement).src).toContain('/static/previews/model/hero_model.png')
  })

  // 3. 动作模块 GIF URL 正确（moduleType=3, animator）
  it('动作模块预览 URL 正确', () => {
    const store = useSearchStore()
    store.moduleType = 3

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ thumbnail_path: 'run_anim.gif' }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })

    const img = wrapper.find('img')
    expect((img.element as HTMLImageElement).src).toContain('/static/previews/animator/run_anim.gif')
  })

  // 4. 特效模块 GIF URL 正确（moduleType=2）
  it('特效模块 GIF URL 正确', () => {
    const store = useSearchStore()
    store.moduleType = 2

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ thumbnail_path: 'explosion.gif' }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })

    const img = wrapper.find('img')
    // Effect uses grid gif when not hovering: /data/gifs/explosion_grid.gif
    expect((img.element as HTMLImageElement).src).toContain('/data/gifs/')
    expect((img.element as HTMLImageElement).src).toContain('_grid.gif')
  })

  // 5. 图标模块 PNG URL 正确（moduleType=4）
  it('图标模块 PNG URL 正确', () => {
    const store = useSearchStore()
    store.moduleType = 4

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ thumbnail_path: 'sword_icon.png', tags: { icon_id: 1001 } }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })

    const img = wrapper.find('img')
    expect((img.element as HTMLImageElement).src).toContain('/data/icons/sword_icon.png')
  })

  // 6. icon 才显示 ID 行（showIdRow = isIcon）
  it('icon 才显示 ID 行', async () => {
    const store = useSearchStore()

    // Non-icon module: ID row should NOT be shown
    store.moduleType = 1
    const modelWrapper = mount(AssetCard, {
      props: { item: makeItem({ tags: { icon_id: 999 } }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })
    expect(modelWrapper.find('.card-icon-id').exists()).toBe(false)

    // Icon module: ID row SHOULD be shown
    store.moduleType = 4
    const iconWrapper = mount(AssetCard, {
      props: { item: makeItem({ tags: { icon_id: 999 } }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })
    expect(iconWrapper.find('.card-icon-id').exists()).toBe(true)
    await iconWrapper.trigger('mouseenter')
    expect(iconWrapper.find('.id-copy-chip').exists()).toBe(false)
  })

  it.each([1, 2, 3, 4])('module %i card exposes resource path copy without opening detail', async (moduleType) => {
    const store = useSearchStore()
    store.moduleType = moduleType

    const wrapper = mount(AssetCard, {
      props: { item: makeItem({ id: moduleType, resource_path: `/resources/module-${moduleType}.asset` }) },
      global: {
        stubs: { AssetDetailModal: true },
      },
    })

    const copyBtn = wrapper.find(`[data-testid="asset-copy-path-${moduleType}"]`)
    expect(copyBtn.exists()).toBe(true)

    await copyBtn.trigger('click')
    await flushPromises()

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(`/resources/module-${moduleType}.asset`)
    expect(wrapper.findComponent({ name: 'AssetDetailModal' }).exists()).toBe(false)
  })
})
