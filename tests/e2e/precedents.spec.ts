import { test, expect } from '@playwright/test';
import { waitForAppReady } from './utils'; // Import the helper

const sampleSearchSummary = 'Water damage in kitchen.';

test.describe('View Precedents Feature', () => {
  test.beforeEach(async ({ page }) => {
    await waitForAppReady(page); // Use the helper
  });

  test('should allow user to search for precedents and view results', async ({ page }) => {
    const searchInput = page.locator('#tour-precedent-input');
    await expect(searchInput).toBeVisible({timeout: 10000});
    await searchInput.fill(sampleSearchSummary);

    const searchButton = page.locator('#tour-precedent-search-button');
    await expect(searchButton).toBeVisible({timeout: 10000});
    await searchButton.click();

    // Wait for results. Precedent results are in a Card within a SimpleGrid.
    // Look for at least one Card element that would represent a precedent.
    // This selector might need refinement based on PrecedentPanel.tsx's exact structure.
    const precedentCardLocator = page.locator('div.chakra-card'); // Assuming precedents are in Chakra Cards
    await expect(precedentCardLocator.first()).toBeVisible({ timeout: 15000 }); // Wait for the first card to appear
    expect(await precedentCardLocator.count()).toBeGreaterThan(0);

    // Further check: a card should contain some text (e.g., part of the precedent details).
    // This is a loose check; more specific content checks can be added.
    await expect(precedentCardLocator.first().locator('p, span, div').filter({ hasText: /./ })).toBeVisible(); 
  });

  test('should display a message if no precedents are found', async ({ page }) => {
    const unlikelySummary = 'XyzzyAbcdef12345NoMatchPossibleSummary';
    const searchInput = page.locator('#tour-precedent-input');
    await expect(searchInput).toBeVisible({timeout: 10000});
    await searchInput.fill(unlikelySummary);

    const searchButton = page.locator('#tour-precedent-search-button');
    await expect(searchButton).toBeVisible({timeout: 10000});
    await searchButton.click();

    // Check for a message indicating no results. 
    // This selector will depend on how PrecedentPanel.tsx displays this message.
    // Assuming it might be a Text component or similar.
    const noResultsMessage = page.getByText(/No precedents found matching your summary/i); // Case-insensitive match
    await expect(noResultsMessage).toBeVisible({ timeout: 10000 });
  });
}); 