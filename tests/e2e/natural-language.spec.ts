import { test, expect } from '@playwright/test';
import {
  gotoApp,
  lastUserBubbleText,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('자연어 메시지 테스트 - 폼 제출 후 자연어 변환 확인', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '호텔 예약하고 싶어요');
  await waitForForm(page);

  await page.fill(selectors.cityInput, '서울');
  await page.click(selectors.formSubmitButton);

  await expect.poll(async () => lastUserBubbleText(page)).toContain('서울에서');

  const message = await lastUserBubbleText(page);
  expect(message).toContain('2026년');
  expect(message).toContain('월');
  expect(message).toContain('일');
  expect(message).toContain('명이 숙박할 호텔을 검색합니다');

  await takeScreenshot(page, 'test-natural-language.png');
});
