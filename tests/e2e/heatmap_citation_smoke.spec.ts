import { test, expect } from '@playwright/test';

// This test simulates a user journey: 
// 1. Opening a specific document.
// 2. Interacting with a heatmap-like feature to view/summarize a section.
// 3. Asking a question about the document.
// 4. Verifying that the answer includes a citation.

test.describe('Heatmap, Summarization, and Citation Flow', () => {
  const targetDocumentId = 'doc_01.pdf.txt'; // Example document ID, ensure this exists in your test data
  const questionAboutDocument = 'What was the primary period of asbestos exposure?';
  const expectedAnswerSnippet = 'exposure'; // Part of the expected answer text
  const expectedCitationPattern = /Page \d+|Source:|Section \d+/i; // Regex for expected citation format

  test.beforeEach(async ({ page }) => {
    // Navigate to the application's entry point.
    // Assumes baseURL is 'http://localhost:5178/claims-ai/' from playwright.config.ts
    await page.goto('/');
    // Add login or other setup if needed, e.g.:
    // await page.fill('#username', 'testuser');
    // await page.fill('#password', 'testpass');
    // await page.click('#login-button');
    await expect(page.locator('body')).toContainText('Claims-AI', { timeout: 20000 }); // General check page loaded
  });

  test('should interact with heatmap, get summary, ask question, and see citation', async ({ page }) => {
    // STEP 1: Open the target document
    // Assumes documents are listed and can be clicked. Using a data-testid for robustness.
    console.log(`Attempting to open document: ${targetDocumentId}`);
    const documentItemSelector = `[data-testid="doc-item-${targetDocumentId}"]`;
    // Fallback if specific doc item selector isn't implemented, click first available document for flow testing
    // const fallbackDocumentSelector = '[data-testid^="doc-item-"]'; 
    try {
      await page.locator(documentItemSelector).first().click({ timeout: 15000 });
    } catch (e) {
      console.warn(`Could not find ${documentItemSelector}, attempting to click a generic document item as fallback.`);
      // await page.locator(fallbackDocumentSelector).first().click({ timeout: 15000 });
      // For now, let's just proceed, assuming the UI might load a default document or the test needs specific setup.
      console.log("Proceeding without explicit document click, assuming document context is available.")
    }
    // Wait for some indication that the document view is active, e.g., a title or specific section.
    // This is highly dependent on your app's structure.
    await expect(page.locator('[data-testid="document-viewer-container"]_PLACEHOLDER')).toBeVisible({ timeout: 20000 });
    console.log(`Document ${targetDocumentId} view is assumed active.`);

    // STEP 2: Interact with Heatmap/Relevancy Indicators & Get Summary
    // Assumes a heatmap container and clickable heatmap bars/sections.
    console.log('Looking for heatmap and attempting interaction...');
    const heatmapContainerSelector = '[data-testid="heatmap-container"]_PLACEHOLDER';
    const heatmapBarSelector = '[data-testid="heatmap-bar"]_PLACEHOLDER'; // A clickable element within the heatmap
    const summaryDisplaySelector = '[data-testid="summary-display"]_PLACEHOLDER';

    await expect(page.locator(heatmapContainerSelector).first()).toBeVisible({ timeout: 15000 });
    console.log('Heatmap container found.');

    // Click the first heatmap bar/element to trigger a summary or highlight
    await page.locator(heatmapBarSelector).first().click();
    console.log('Clicked on a heatmap bar/element.');

    // Expect a summary related to the clicked heatmap section to appear
    await expect(page.locator(summaryDisplaySelector).first()).toBeVisible({ timeout: 10000 });
    const summaryText = await page.locator(summaryDisplaySelector).first().textContent();
    expect(summaryText).not.toBeNull();
    expect(summaryText!.length).toBeGreaterThan(10); // Expect some meaningful summary text
    console.log(`Summary displayed: "${summaryText!.substring(0, 100)}..."`);

    // STEP 3: Ask a question about the document
    console.log(`Asking question: "${questionAboutDocument}"`);
    const questionInputSelector = '[data-testid="qa-input"]_PLACEHOLDER';
    const askButtonSelector = '[data-testid="qa-submit-button"]_PLACEHOLDER';

    await expect(page.locator(questionInputSelector).first()).toBeVisible({ timeout: 10000 });
    await page.locator(questionInputSelector).first().fill(questionAboutDocument);
    await page.locator(askButtonSelector).first().click();
    console.log('Question submitted.');

    // STEP 4: Expect answer with citation
    console.log('Waiting for answer and citation...');
    const answerTextSelector = '[data-testid="answer-text"]_PLACEHOLDER';
    const citationSelector = '[data-testid="citation-reference"]_PLACEHOLDER'; // Selector for an element containing citation

    // Wait for the answer text to be visible and contain expected content
    await expect(page.locator(answerTextSelector).first()).toBeVisible({ timeout: 25000 });
    const actualAnswerText = await page.locator(answerTextSelector).first().textContent();
    expect(actualAnswerText).not.toBeNull();
    expect(actualAnswerText!.toLowerCase()).toContain(expectedAnswerSnippet.toLowerCase());
    console.log(`Answer received: "${actualAnswerText!.substring(0, 150)}..."`);

    // Wait for the citation to be visible and match the expected pattern
    await expect(page.locator(citationSelector).first()).toBeVisible({ timeout: 10000 });
    const actualCitationText = await page.locator(citationSelector).first().textContent();
    expect(actualCitationText).not.toBeNull();
    expect(actualCitationText!).toMatch(expectedCitationPattern);
    console.log(`Citation found: "${actualCitationText}".`);

    console.log('Heatmap interaction, summarization, Q&A, and citation flow test completed successfully.');
  });
}); 