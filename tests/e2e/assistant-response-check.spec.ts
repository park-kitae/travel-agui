import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('응답 내용 확인 - 메시지, 툴 호출, 폼 검증', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');
  await waitForForm(page);

  await expect(page.locator(selectors.messageRows)).toHaveCount(2);
  await expect(page.locator(selectors.userBubble)).toHaveCount(1);
  await expect(page.locator(selectors.assistantBubble)).toHaveCount(1);
  await expect(page.locator(selectors.toolCall)).toHaveCount(1);
  await expect(page.locator(selectors.toolCallLabel)).toContainText(['request_user_input']);
  await expect(page.locator(selectors.form)).toBeVisible();

  await takeScreenshot(page, 'test-response-check.png');
});
