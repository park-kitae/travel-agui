import { test, expect } from '@playwright/test';
import {
  clearConversation,
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForFlightResults,
  waitForForm,
  waitForHotelResults,
} from './utils/testHelpers';

test('전체 플로우 테스트 - 호텔 + 항공편', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '서울 호텔 알려줘');
  await waitForForm(page);
  await expect(page.locator(selectors.cityInput)).toHaveValue('서울');
  await page.click(selectors.formSubmitButton);
  await waitForHotelResults(page);
  await expect(page.locator(selectors.hotelItem).first()).toBeVisible();

  await clearConversation(page);

  await sendUserMessage(page, '서울에서 도쿄 가는 항공편');
  await waitForForm(page);
  await expect(page.locator(selectors.originInput)).toHaveValue('서울');
  await expect(page.locator(selectors.destinationInput)).toHaveValue('도쿄');
  await expect(page.locator(selectors.tripTypeSelect)).toHaveValue('왕복');
  await page.click(selectors.formSubmitButton);
  await waitForFlightResults(page);

  await expect(page.locator(selectors.flightItem)).toHaveCount(6);
  await expect(page.locator(selectors.flightSection)).toHaveCount(2);
  await expect(page.locator(selectors.airlineName).first()).not.toBeEmpty();

  await takeScreenshot(page, 'test-full-flow.png');
});
