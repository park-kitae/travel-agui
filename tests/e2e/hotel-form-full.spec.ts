import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
  waitForHotelResults,
} from './utils/testHelpers';

test('호텔 예약 폼 완전 테스트 - 초기 확인부터 검색 결과까지', async ({ page }) => {
  await gotoApp(page);

  await expect(page.locator(selectors.welcomeTitle)).toContainText('어디로 떠나고 싶으신가요?');

  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');
  await waitForForm(page);

  await expect(page.locator(selectors.checkInInput)).toBeVisible();
  await expect(page.locator(selectors.checkOutInput)).toBeVisible();
  await expect(page.locator(selectors.guestsInput)).toBeVisible();

  await page.fill(selectors.checkInInput, '2024-06-10');
  await page.fill(selectors.checkOutInput, '2024-06-14');
  await page.fill(selectors.guestsInput, '2');
  await page.click(selectors.formSubmitButton);

  await waitForHotelResults(page);

  await expect(page.locator(selectors.toolCard)).toHaveCount(1);
  await expect(page.locator(selectors.hotelItem)).toHaveCount(3);
  await expect(page.locator(selectors.hotelName).first()).not.toBeEmpty();
  await expect(page.locator(selectors.hotelPrice).first()).not.toBeEmpty();

  await takeScreenshot(page, 'test-hotel-form-complete.png');
});
