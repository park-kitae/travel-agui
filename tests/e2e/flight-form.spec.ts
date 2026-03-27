import { test, expect } from '@playwright/test';
import {
  clearConversation,
  gotoApp,
  lastUserBubbleText,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('항공편 폼 테스트 - 기본값 및 자동 입력', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '항공편 검색하고 싶어요');
  await waitForForm(page);

  await expect(page.locator(selectors.originInput)).toHaveValue('');
  await expect(page.locator(selectors.destinationInput)).toHaveValue('');
  await expect(page.locator(selectors.tripTypeSelect)).toHaveValue('왕복');
  await expect(page.locator(selectors.passengersInput)).toHaveValue('1');
  await expect(page.locator(selectors.departureDateInput)).not.toHaveValue('');
  await expect(page.locator(selectors.returnDateInput)).not.toHaveValue('');

  await page.fill(selectors.originInput, '서울');
  await page.fill(selectors.destinationInput, '도쿄');
  await page.click(selectors.formSubmitButton);

  await expect.poll(async () => lastUserBubbleText(page)).toContain('서울에서 도쿄까지');
  const submittedMessage = await lastUserBubbleText(page);
  expect(submittedMessage).toContain('왕복');
  expect(submittedMessage).toContain('2026년');

  await clearConversation(page);

  await sendUserMessage(page, '서울에서 오사카 가는 항공편 알려줘');
  await waitForForm(page);
  await expect(page.locator(selectors.originInput)).toHaveValue('서울');
  await expect(page.locator(selectors.destinationInput)).toHaveValue('오사카');

  await takeScreenshot(page, 'test-flight-form.png');
});
