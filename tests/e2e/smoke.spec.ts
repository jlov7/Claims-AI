import { test, expect } from '@playwright/test';
import { waitForAppReady } from './utils'; // Import the helper

// Make sure to create this file and put some sample content in it.
const sampleFile = 'tests/e2e/fixtures/sample.pdf'; 

test.describe('Smoke Test - Core UI and Document Upload', () => {
  test.beforeEach(async ({ page }) => {
    await waitForAppReady(page); // Use the helper
  });

  test('should display core UI elements', async ({ page }) => {
    // Main heading check is now in waitForAppReady
    await expect(page.getByText('Drag & drop files here, or click to select files.')).toBeVisible({ timeout: 10000 });

    const chatInputLocator = page.locator('#tour-chat-input');
    // No need for .waitFor({ state: 'attached' }) if #app-ready guarantees component presence
    await expect(chatInputLocator).toBeVisible({ timeout: 10000 }); 
    
    // Restore these checks
    await expect(page.getByRole('heading', { name: 'Generate Claim Strategy Note' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Find Nearest Precedents' })).toBeVisible({ timeout: 10000 });
  });

  test('should upload a document successfully', async ({ page }) => {
    const fileName = sampleFile.split('/').pop()!;
    const fileChooserPromise = page.waitForEvent('filechooser');
    
    const uploaderElement = page.locator('#tour-file-uploader');
    await expect(uploaderElement).toBeVisible({timeout: 10000});
    await uploaderElement.click(); 
    
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(sampleFile);

    const uploadButton = page.getByRole('button', { name: /Upload Selected \(\d+\)/ });
    await expect(uploadButton).toBeVisible({timeout: 10000});
    await uploadButton.click();

    // Use the new robust selector for the success icon
    const successIcon = page.locator(
      `div.chakra-table__tr:has-text("${fileName}") >> css=svg[data-icon="check-circle"]`
    );
    await expect(successIcon).toBeVisible({ timeout: 20000 });
  });
}); 