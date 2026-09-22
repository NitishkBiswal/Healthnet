import { test, expect } from '@playwright/test';

test.describe('HealthNet Landing Page', () => {
  test('should display HealthNet title', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'HealthNet' })).toBeVisible();
  });

  test('should show system status section', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('System Status')).toBeVisible();
  });
});
