import { test, expect, type Page } from '@playwright/test';
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

function toSseEvent(event: Record<string, unknown>): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

async function stubAguiRunStream(
  page: Page,
  chunks: Array<{ parts: string[]; delayMs?: number }>,
) {
  await page.addInitScript(({ streamChunks }: { streamChunks: Array<{ parts: string[]; delayMs: number }> }) => {
    const originalFetch = window.fetch.bind(window);
    const encoder = new TextEncoder();

    window.fetch = async (input, init) => {
      const url = typeof input === 'string'
        ? input
        : input instanceof Request
        ? input.url
        : String(input);

      if (!url.includes('/agui/run')) {
        return originalFetch(input, init);
      }

      const stream = new ReadableStream({
        async start(controller) {
          for (const chunk of streamChunks) {
            if (chunk.delayMs) {
              await new Promise(resolve => window.setTimeout(resolve, chunk.delayMs));
            }

            for (const part of chunk.parts) {
              controller.enqueue(encoder.encode(part));
            }
          }
          controller.close();
        },
      });

      return new Response(stream, {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
        },
      });
    };
  }, {
    streamChunks: chunks.map(chunk => ({
      parts: chunk.parts,
      delayMs: chunk.delayMs ?? 0,
    })),
  });
}

async function observeAssistantBubbleStates(
  page: Page,
  bubbleIndex: number,
  states: string[],
) {
  await page.exposeFunction('captureAssistantBubbleState', (text: string) => {
    if (states.at(-1) !== text) {
      states.push(text);
    }
  });

  await page.evaluate((targetBubbleIndex: number) => {
    const runtimeWindow = window as Window & {
      captureAssistantBubbleState?: (text: string) => void;
    };

    const normalizeText = (value: string | null | undefined) => value?.replace(/\s+/g, ' ').trim() ?? '';

    const recordBubbleText = (bubble: Element | null) => {
      const text = normalizeText(bubble?.textContent);
      if (text && text !== '생각 중...') {
        runtimeWindow.captureAssistantBubbleState?.(text);
      }
    };

    const observeBubble = (bubble: Element) => {
      recordBubbleText(bubble);
      const bubbleObserver = new MutationObserver(() => {
        recordBubbleText(bubble);
      });

      bubbleObserver.observe(bubble, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    };

    const getTargetBubble = () => document.querySelectorAll('.bubble-assistant').item(targetBubbleIndex);
    const existingBubble = getTargetBubble();
    if (existingBubble) {
      observeBubble(existingBubble);
      return;
    }

    const listObserver = new MutationObserver(() => {
      const bubble = getTargetBubble();
      if (!bubble) {
        return;
      }

      listObserver.disconnect();
      observeBubble(bubble);
    });

    listObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }, bubbleIndex);
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

test('응답 캡처 테스트 - 한 응답에서 여러 TEXT_MESSAGE_CHUNK를 순서대로 렌더링한다', async ({ page }) => {
  const assistantBubbleStates: string[] = [];

  await stubAguiRunStream(page, [
    {
      parts: [
        toSseEvent({ type: 'RUN_STARTED', runId: 'run-text-chunks', threadId: 'thread-text-chunks' }),
        'data: {"type":"TEXT_MESSAGE_CHUNK","del',
      ],
    },
    {
      delayMs: 50,
      parts: [
        'ta":"안녕"}\n\n',
      ],
    },
    {
      delayMs: 100,
      parts: [
        toSseEvent({ type: 'TEXT_MESSAGE_CHUNK', delta: '하세요' }),
        toSseEvent({ type: 'RUN_FINISHED', runId: 'run-text-chunks', threadId: 'thread-text-chunks' }),
      ],
    },
  ]);
  
  await gotoApp(page);
  const assistantBubbleIndex = await page.locator(selectors.assistantBubble).count();
  await observeAssistantBubbleStates(page, assistantBubbleIndex, assistantBubbleStates);
  await sendUserMessage(page, '인사해줘');

  const assistantBubble = page.locator(selectors.assistantBubble).nth(assistantBubbleIndex);
  await expect(assistantBubble).toHaveText('안녕하세요');
  await expect.poll(() => assistantBubbleStates).toEqual(['안녕', '안녕하세요']);
});
