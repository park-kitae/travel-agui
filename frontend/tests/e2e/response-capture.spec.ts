import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('응답 캡처 테스트 - 폼 요청 응답 확인', async ({ page }) => {
  const responses: string[] = [];

  page.on('response', async response => {
    if (!response.url().includes('/agui/run')) {
      return;
    }

    try {
      responses.push(await response.text());
    } catch {
      responses.push('');
    }
  });

  await gotoApp(page);
  await sendUserMessage(page, '호텔 예약하고 싶어요');
  await waitForForm(page);

  await expect.poll(() => responses.length).toBeGreaterThan(0);
  expect(responses.some(body => body.includes('USER_INPUT_REQUEST') || body.includes('request_user_input'))).toBeTruthy();
  await expect(page.locator(selectors.form)).toBeVisible();

  await takeScreenshot(page, 'test-capture-response.png');
});
