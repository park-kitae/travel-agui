import { expect, type Page } from '@playwright/test';

export const BASE_URL = 'http://localhost:5173';

export const selectors = {
  inputBox: '.input-box',
  sendButton: '.send-btn',
  clearButton: '.clear-btn',
  welcomeTitle: '.welcome-title',
  form: '.user-input-form',
  formSubmitButton: '.form-submit-btn',
  messageRows: '.message-row',
  bubble: '.bubble',
  userBubble: '.bubble-user',
  assistantBubble: '.bubble-assistant',
  toolCall: '.tool-call-item',
  toolCallLabel: '.tool-call-label',
  toolCard: '.tool-card',
  hotelItem: '.hotel-item',
  hotelItemClickable: '.hotel-item.clickable-hotel',
  hotelName: '.hotel-name',
  hotelPrice: '.hotel-price',
  hotelDetailCard: '.hotel-detail-card',
  hotelDetailDescription: '.hotel-detail-description',
  hotelRoomItem: '.hotel-room-item',
  hotelAmenityTag: '.hotel-amenity-tag',
  hotelHighlightTag: '.hotel-highlight-tag',
  hotelDetailPolicies: '.hotel-detail-policies',
  flightItem: '.flight-item',
  flightSection: '.flight-section',
  airlineName: '.airline-name',
  errorBubble: '.bubble-error',
  cityInput: 'input[id="city"]',
  checkInInput: 'input[id="check_in"]',
  checkOutInput: 'input[id="check_out"]',
  guestsInput: 'input[id="guests"]',
  originInput: 'input[id="origin"]',
  destinationInput: 'input[id="destination"]',
  tripTypeSelect: 'select[id="trip_type"]',
  departureDateInput: 'input[id="departure_date"]',
  returnDateInput: 'input[id="return_date"]',
  passengersInput: 'input[id="passengers"]',
} as const;

export async function gotoApp(page: Page): Promise<void> {
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');
}

export async function sendUserMessage(page: Page, message: string): Promise<void> {
  await page.fill(selectors.inputBox, message);
  await page.click(selectors.sendButton);
}

export async function waitForForm(page: Page, timeout = 15000): Promise<void> {
  await expect(page.locator(selectors.form)).toBeVisible({ timeout });
}

export async function clearConversation(page: Page): Promise<void> {
  await page.click(selectors.clearButton);
  await page.waitForTimeout(1000);
}

export async function waitForHotelResults(page: Page, timeout = 15000): Promise<void> {
  await expect(page.locator(selectors.hotelItem).first()).toBeVisible({ timeout });
}

export async function waitForFlightResults(page: Page, timeout = 15000): Promise<void> {
  await expect(page.locator(selectors.flightItem).first()).toBeVisible({ timeout });
}

export async function waitForToolCard(page: Page, timeout = 15000): Promise<void> {
  await expect(page.locator(selectors.toolCard).first()).toBeVisible({ timeout });
}

export async function lastUserBubbleText(page: Page): Promise<string> {
  const texts = await page.locator(selectors.userBubble).allTextContents();
  return texts.at(-1)?.trim() ?? '';
}

export async function takeScreenshot(page: Page, fileName: string): Promise<void> {
  await page.screenshot({
    path: `tests/e2e/test-results/${fileName}`,
    fullPage: true,
  });
}
