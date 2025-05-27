import { test, expect } from '@playwright/test';
import { waitForAppReady } from './utils';

const sampleContent = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.';

test.describe('Summarise Feature', () => {
  test.beforeEach(async ({ page }) => {
    await waitForAppReady(page);
    // Ensure the summarise panel has rendered
    const panel = page.locator('#tour-summarise-panel');
    await expect(panel).toBeVisible({ timeout: 10000 });
  });

  test('should allow user to summarise pasted text', async ({ page }) => {
    const panel = page.locator('#tour-summarise-panel');
    const contentInput = panel.locator('textarea#tour-summarise-content');
    await expect(contentInput).toBeVisible({ timeout: 10000 });
    await contentInput.fill(sampleContent);

    const button = panel.getByRole('button', { name: 'Get Summary' });
    await expect(button).toBeVisible({ timeout: 10000 });
    await button.click();

    const resultBox = panel.locator('#tour-summarise-results');
    await expect(resultBox).toBeVisible({ timeout: 20000 });
    const summaryText = await resultBox.innerText();
    expect(summaryText).toBe('This is a dummy summary.');
  });

  test('should allow user to summarise by document ID', async ({ page }) => {
    const panel = page.locator('#tour-summarise-panel');
    const idInput = panel.locator('input#tour-summarise-id');
    await expect(idInput).toBeVisible({ timeout: 10000 });
    await idInput.fill('ignored');

    const button = panel.getByRole('button', { name: 'Get Summary' });
    await expect(button).toBeVisible({ timeout: 10000 });
    await button.click();

    const resultBox = panel.locator('#tour-summarise-results');
    await expect(resultBox).toBeVisible({ timeout: 20000 });
    const summaryText = await resultBox.innerText();
    expect(summaryText).toBe('This is a dummy summary.');
  });
}); 