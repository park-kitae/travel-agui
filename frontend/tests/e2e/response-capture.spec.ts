import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

function toSseBody(events: Array<Record<string, unknown>>): string {
  return events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('');
}

test('응답 캡처 테스트 - 폼 요청 응답 확인', async ({ page }) => {
  const responses: string[] = [];

  await page.route('**/agui/run', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: toSseBody([
        { type: 'RUN_STARTED', runId: 'run-form', threadId: 'thread-form' },
        {
          type: 'USER_INPUT_REQUEST',
          requestId: 'req-1',
          inputType: 'hotel_booking_details',
          fields: [
            { name: 'check_in', type: 'date', label: '체크인', required: true },
          ],
        },
        { type: 'RUN_FINISHED', runId: 'run-form', threadId: 'thread-form' },
      ]),
    });
  });

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

test('응답 캡처 테스트 - STATE_DELTA 응답 확인', async ({ page }) => {
  const responses: string[] = [];

  await page.route('**/agui/run', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: toSseBody([
        { type: 'RUN_STARTED', runId: 'run-1', threadId: 'thread-1' },
        {
          type: 'STATE_DELTA',
          delta: [
            { op: 'replace', path: '/travel_context/destination', value: '도쿄' },
            { op: 'replace', path: '/agent_status/current_intent', value: 'searching' },
          ],
        },
        { type: 'RUN_FINISHED', runId: 'run-1', threadId: 'thread-1' },
      ]),
    });
  });

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
  await sendUserMessage(page, '도쿄 호텔 알려줘');

  await expect.poll(() => responses.length).toBeGreaterThan(0);
  expect(responses.some(body => body.includes('STATE_DELTA'))).toBeTruthy();
  await expect(page.locator('.sp-field', { hasText: '도착지' }).locator('.sp-field-value')).toHaveText('도쿄');
});
