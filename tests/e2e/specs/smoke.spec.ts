import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'

test('smoke', async ({ page }) => {
  const sp = new SearchPage(page)
  await sp.goto()
  await expect(sp.searchInput).toBeVisible()
})
