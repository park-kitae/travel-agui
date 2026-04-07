import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
} from './utils/testHelpers';

test('디버깅용 - 전체 플로우 모니터링', async ({ page }) => {
  const networkEvents: string[] = [];

  page.on('request', request => {
    if (request.url().includes('/agui/')) {
      networkEvents.push(`${request.method()} ${request.url()}`);
    }
  });

  await gotoApp(page);
  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');

  await expect.poll(async () => {
    const formCount = await page.locator(selectors.form).count();
    const toolCardCount = await page.locator(selectors.toolCard).count();
    const errorCount = await page.locator(selectors.errorBubble).count();
    return { formCount, toolCardCount, errorCount };
  }).toEqual({ formCount: 1, toolCardCount: 0, errorCount: 0 });

  expect(networkEvents.some(event => event.includes('/agui/'))).toBeTruthy();
  await takeScreenshot(page, 'test-form-captured.png');
});
