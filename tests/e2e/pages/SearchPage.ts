import { Page, expect } from '@playwright/test'
import { ModuleTabs } from './ModuleTabs'
import { FilterPanel } from './FilterPanel'
import { ResultGrid } from './ResultGrid'
import { AssetDetailModal } from './AssetDetailModal'

export class SearchPage {
  constructor(private page: Page) {}

  async goto() { await this.page.goto('http://localhost:18081') }

  get searchInput() { return this.page.locator('[data-testid="search-input"]') }
  get moduleTabs() { return new ModuleTabs(this.page) }
  get filterPanel() { return new FilterPanel(this.page) }
  get resultGrid() { return new ResultGrid(this.page) }
  get detailModal() { return new AssetDetailModal(this.page) }

  async search(text: string) {
    await this.searchInput.fill(text)
    await this.page.waitForLoadState('networkidle')
  }

  async clearSearch() {
    await this.searchInput.fill('')
    await this.page.waitForLoadState('networkidle')
  }

  async expectQueryTimeLessThan(ms: number) {
    const resp = await this.page.waitForResponse(r =>
      r.url().includes('/api/v1/search/query') && r.status() === 200
    )
    const body = await resp.json()
    expect(body.query_time_ms).toBeLessThan(ms)
  }
}
