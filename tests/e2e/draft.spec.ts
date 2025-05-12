import { test, expect } from '@playwright/test';
import { waitForAppReady } from './utils'; // Import the helper

const sampleClaimSummary = 'Claim about a broken window.';
const defaultOutputFilename = 'ClaimStrategyNote.docx';

test.describe('Draft Strategy Note Feature', () => {
  test.beforeEach(async ({ page }) => {
    await waitForAppReady(page); // Use the helper
  });

  test('should allow user to draft and download a strategy note', async ({ page }) => {
    // Ensure the claim summary input is visible before filling
    const summaryInput = page.locator('#tour-draft-summary');
    await expect(summaryInput).toBeVisible({timeout: 10000});
    await summaryInput.fill(sampleClaimSummary);

    const filenameInput = page.locator('#tour-draft-filename');
    await expect(filenameInput).toBeVisible({timeout: 10000});
    // Optional: clear and fill if needed, or check default value
    // await filenameInput.clear(); 
    // await filenameInput.fill('MyCustomStrategyNote.docx');

    const downloadPromise = page.waitForEvent('download');
    // Ensure the download button is visible before clicking
    const downloadButton = page.getByRole('button', { name: 'Download Strategy Note' });
    await expect(downloadButton).toBeVisible({timeout: 10000});
    await downloadButton.click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(defaultOutputFilename); // Or your custom name if changed
    // Optional: Save the file to check its content, though this can be complex.
    // await download.saveAs('./playwright-report/downloads/' + download.suggestedFilename());
  });
}); 