import { expect, test } from '@playwright/test';
import { gotoApp, selectors, sendUserMessage } from './utils/testHelpers';

function toSseBody(events: Array<Record<string, unknown>>): string {
  return events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('');
}

test('A2UI_MESSAGE renders a favorite preference surface', async ({ page }) => {
  const surfaceId = 'favorite-req-a2ui';
  const requestBodies: Array<Record<string, unknown>> = [];

  await page.route('**/agui/run', async route => {
    const requestBody = route.request().postDataJSON() as Record<string, unknown>;
    requestBodies.push(requestBody);

    if (requestBodies.length > 1) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: toSseBody([
          { type: 'TEXT_MESSAGE_CHUNK', delta: '취향을 반영했습니다.' },
          { type: 'RUN_FINISHED', runId: 'run-a2ui-done', threadId: 'thread-a2ui' },
        ]),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: toSseBody([
        { type: 'RUN_STARTED', runId: 'run-a2ui', threadId: 'thread-a2ui' },
        {
          type: 'A2UI_MESSAGE',
          surfaceId,
          requestId: 'req-a2ui',
          favoriteType: 'hotel_preference',
          messages: [
            {
              version: 'v0.9',
              createSurface: {
                surfaceId,
                catalogId: 'https://a2ui.org/specification/v0_9/basic_catalog.json',
              },
            },
            {
              version: 'v0.9',
              updateComponents: {
                surfaceId,
                components: [
                  { id: 'root', component: 'Card', child: 'form' },
                  { id: 'form', component: 'Column', children: ['title', 'grade', 'submit'] },
                  { id: 'title', component: 'Text', text: '호텔 취향을 선택해주세요' },
                  {
                    id: 'grade',
                    component: 'ChoicePicker',
                    label: '호텔 등급',
                    variant: 'mutuallyExclusive',
                    options: [{ label: '5성', value: '5성' }],
                    value: { path: '/hotel_grade' },
                  },
                  { id: 'submit-label', component: 'Text', text: '선택 완료' },
                  {
                    id: 'submit',
                    component: 'Button',
                    variant: 'primary',
                    child: 'submit-label',
                    action: {
                      event: {
                        name: 'submit_favorite_preferences',
                        context: {
                          requestId: 'req-a2ui',
                          favoriteType: 'hotel_preference',
                          hotel_grade: { path: '/hotel_grade' },
                        },
                      },
                    },
                  },
                ],
              },
            },
            {
              version: 'v0.9',
              updateDataModel: {
                surfaceId,
                value: {
                  requestId: 'req-a2ui',
                  favoriteType: 'hotel_preference',
                  hotel_grade: [],
                },
              },
            },
          ],
        },
        { type: 'RUN_FINISHED', runId: 'run-a2ui', threadId: 'thread-a2ui' },
      ]),
    });
  });

  await gotoApp(page);
  await sendUserMessage(page, '호텔 추천해줘');

  const assistantMessage = page.locator(`${selectors.messageRows}.assistant`).last();
  await expect(assistantMessage.locator('.ui-a2ui-surface')).toBeVisible();
  await expect(assistantMessage).toContainText('호텔 취향을 선택해주세요');
  await expect(assistantMessage).toContainText('호텔 등급');

  await assistantMessage.getByRole('radio', { name: '5성' }).click();
  await assistantMessage.getByRole('button', { name: '선택 완료' }).click();

  await expect.poll(() => requestBodies.length).toBe(2);
  const secondBody = requestBodies[1];
  const state = secondBody.state as { user_preferences?: Record<string, unknown> };
  expect(state.user_preferences?.hotel_grade).toEqual(['5성']);
});
