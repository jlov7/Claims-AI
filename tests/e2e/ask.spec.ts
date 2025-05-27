import { test, expect } from '@playwright/test';
import { waitForAppReady } from './utils'; // Import the helper

const sampleFile = 'tests/e2e/fixtures/sample.pdf';
const testQuestion = 'What is this document about?';

test.describe('Ask (RAG) Feature', () => {
  test.beforeEach(async ({ page }) => {
    await waitForAppReady(page); // Use the helper

    // Upload a document before each test in this suite
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

  test('should allow user to ask a question and receive an answer with sources', async ({ page }) => {
    const chatInputLocator = page.locator('#tour-chat-input');
    await expect(chatInputLocator).toBeVisible({ timeout: 10000 });
    await chatInputLocator.fill(testQuestion);
    
    await page.getByRole('button', { name: 'Send' }).click();

    const aiMessageLocator = page.locator('.chat-message-ai:not(:empty):has(p), .chat-message-ai:not(:empty):has(div[class*="markdown"] p)').last();
    await expect(aiMessageLocator).toBeVisible({ timeout: 20000 });
    await expect(aiMessageLocator).not.toContainText('Error:', { timeout: 1000 });

    const sourceTagLocator = aiMessageLocator.locator('span.chakra-tag');
    await expect(sourceTagLocator.first()).toBeVisible({ timeout: 5000 });
    expect(await sourceTagLocator.count()).toBeGreaterThan(0);
  });
}); 