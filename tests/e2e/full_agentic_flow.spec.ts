import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5178/claims-ai/';
const DEFAULT_TIMEOUT = 30000; // Default timeout for many actions
const UPLOAD_PROCESSING_TIMEOUT = 90000; // Increased timeout for upload and subsequent processing (summary)
const QA_TIMEOUT = 45000;
const DRAFT_TIMEOUT = 60000;
const KAFKA_INSPECTOR_TIMEOUT = 20000;

// Helper function to introduce delays for observing test execution (remove in CI)
// const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

test.describe('Full Agentic Flow E2E Test', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    test.setTimeout(240000); // 4 minutes for the whole test to be safe for all steps
    await page.goto(BASE_URL);
    await expect(page.locator('body')).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    console.log('Navigated to base URL for full agentic flow test.');
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('should complete document upload, summarization, Q&A, drafting, and verify Kafka output via UI', async () => {
    // --- 1. Document Upload ---
    console.log('Starting Step 1: Document Upload');
    const fileInputSelector = '[data-testid="file-upload-input"]_PLACEHOLDER';
    const uploadButtonSelector = '[data-testid="file-upload-button"]_PLACEHOLDER';
    const sampleDocumentPath = './test_document.txt'; // Ensure this file exists with relevant text

    await expect(page.locator(fileInputSelector).first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await page.locator(fileInputSelector).first().setInputFiles(sampleDocumentPath);
    console.log(`File selected: ${sampleDocumentPath}`);
    
    if (await page.locator(uploadButtonSelector).first().isVisible({timeout: 5000})) { // Check if button is present
        await page.locator(uploadButtonSelector).first().click();
        console.log('Upload button clicked.');
    }
    console.log('Step 1: Document Upload initiated.');

    // --- 2. Wait for/Verify Summarization (UI Indication) ---
    console.log('Starting Step 2: Wait for Summarization');
    const summaryDisplaySelector = '[data-testid="summary-display-area"]_PLACEHOLDER';
    
    await expect(page.locator(summaryDisplaySelector).first()).toBeVisible({ timeout: UPLOAD_PROCESSING_TIMEOUT });
    await expect(page.locator(summaryDisplaySelector).first()).not.toBeEmpty({ timeout: UPLOAD_PROCESSING_TIMEOUT });
    const summaryText = await page.locator(summaryDisplaySelector).first().textContent();
    expect(summaryText!.length).toBeGreaterThan(10);
    console.log(`Step 2: Summarization complete. Summary snippet: ${summaryText!.substring(0,100)}...`);

    // --- 3. Ask a Question ---
    console.log('Starting Step 3: Ask a Question');
    const qaInputSelector = '[data-testid="qa-input"]_PLACEHOLDER';
    const qaSubmitButtonSelector = '[data-testid="qa-submit-button"]_PLACEHOLDER';
    const question = 'What was the primary diagnosis mentioned?';
    
    await expect(page.locator(qaInputSelector).first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await page.locator(qaInputSelector).first().fill(question);
    await page.locator(qaSubmitButtonSelector).first().click();
    console.log(`Step 3: Question "${question}" submitted.`);

    // --- 4. Verify Answer Received ---
    console.log('Starting Step 4: Verify Answer');
    const answerTextSelector = '[data-testid="answer-text"]_PLACEHOLDER';
    
    await expect(page.locator(answerTextSelector).first()).toBeVisible({ timeout: QA_TIMEOUT });
    const answerText = await page.locator(answerTextSelector).first().textContent();
    expect(answerText).not.toBeNull();
    expect(answerText!.toLowerCase()).toContain('mesothelioma');
    console.log(`Step 4: Answer received: ${answerText!.substring(0,100)}...`);

    // --- 5. Initiate Drafting ---
    console.log('Starting Step 5: Initiate Drafting');
    const draftButtonSelector = '[data-testid="initiate-draft-button"]_PLACEHOLDER';
    
    await expect(page.locator(draftButtonSelector).first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await page.locator(draftButtonSelector).first().click();
    console.log('Step 5: Drafting initiated.');

    // --- 6. Verify Draft Generation (UI Indication) ---
    console.log('Starting Step 6: Verify Draft Generation');
    const draftDisplaySelector = '[data-testid="draft-display-area"]_PLACEHOLDER';

    await expect(page.locator(draftDisplaySelector).first()).toBeVisible({ timeout: DRAFT_TIMEOUT });
    await expect(page.locator(draftDisplaySelector).first()).not.toBeEmpty({ timeout: DRAFT_TIMEOUT });
    const draftText = await page.locator(draftDisplaySelector).first().textContent();
    expect(draftText!.length).toBeGreaterThan(20);
    console.log(`Step 6: Draft generated. Draft snippet: ${draftText!.substring(0,100)}...`);

    // --- 7. Kafka Output Verification (via UI Inspector) ---
    console.log('Starting Step 7: Kafka Output Verification via UI Inspector');
    const showKafkaInspectorButtonSelector = '[data-testid="show-kafka-inspector-button"]_PLACEHOLDER'; 
    const kafkaInspectorModalSelector = '[data-testid="kafka-inspector-modal"]_PLACEHOLDER';
    const kafkaInspectorMessagesSelector = '[data-testid="kafka-message-item"]_PLACEHOLDER';

    await expect(page.locator(showKafkaInspectorButtonSelector).first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    await page.locator(showKafkaInspectorButtonSelector).first().click();
    console.log('Kafka Inspector button clicked.');

    await expect(page.locator(kafkaInspectorModalSelector).first()).toBeVisible({ timeout: DEFAULT_TIMEOUT });
    console.log('Kafka Inspector modal is visible.');

    await expect(page.locator(kafkaInspectorMessagesSelector).last()).toBeVisible({ timeout: KAFKA_INSPECTOR_TIMEOUT });
    console.log('Kafka messages are visible in the inspector.');

    const lastMessageText = await page.locator(kafkaInspectorMessagesSelector).last().textContent();
    expect(lastMessageText).not.toBeNull();
    console.log(`Last Kafka message in inspector: ${lastMessageText!.substring(0, 200)}...`);
    
    expect(lastMessageText!.toLowerCase()).toContain('claim_id');
    expect(lastMessageText!.toLowerCase()).toContain('summary');
    expect(lastMessageText!.toLowerCase()).toContain('question_answer_pairs');
    expect(lastMessageText!.toLowerCase()).toContain('draft_content');
    console.log('Step 7: Kafka output verified in UI Inspector.');

    console.log('Full agentic flow E2E test completed successfully.');
  });
}); 