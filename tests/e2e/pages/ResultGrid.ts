import { Page, Locator, expect } from '@playwright/test'

export class ResultGrid {
  constructor(private page: Page) {}

  get grid(): Locator {
    return this.page.locator('[data-testid="result-grid"]')
  }

  card(id: string | number): Locator {
    return this.page.locator(`[data-testid="asset-card-${id}"]`)
  }

  firstCard(): Locator {
    return this.page.locator('[data-testid^="asset-card-"]').first()
  }

  cards(): Locator {
    return this.page.locator('[data-testid^="asset-card-"]')
  }

  async expectCardCount(n: number) {
    await expect(this.cards()).toHaveCount(n)
  }

  async expectAtLeastOneCard() {
    await expect(this.firstCard()).toBeVisible()
  }
}
