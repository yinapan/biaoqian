import { Page, Locator, expect } from '@playwright/test'

export class ModuleTabs {
  constructor(private page: Page) {}

  tab(n: 1 | 2 | 3 | 4): Locator {
    return this.page.locator(`[data-testid="module-tab-${n}"]`)
  }

  async clickTab(n: 1 | 2 | 3 | 4) {
    await this.tab(n).click()
    await this.page.waitForLoadState('networkidle')
  }

  async expectActive(n: 1 | 2 | 3 | 4) {
    // Element Plus active tab has is-active class
    await expect(this.tab(n)).toHaveClass(/is-active/)
  }
}
