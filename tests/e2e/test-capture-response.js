// 에이전트 응답 캡처 테스트
const { chromium } = require('playwright');

(async () => {
  console.log('🔍 응답 캡처 테스트 시작\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 네트워크 요청/응답 캡처
  const responses = [];
  page.on('response', async (response) => {
    if (response.url().includes('/agui/run')) {
      console.log('📡 /agui/run 응답 감지됨');

      try {
        // SSE 응답을 텍스트로 받기
        const body = await response.text();
        console.log('응답 내용:\n', body.substring(0, 2000), '\n...\n');
        responses.push(body);
      } catch (e) {
        console.log('응답 읽기 실패:', e.message);
      }
    }
  });

  // 콘솔 로그도 캡처
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[UserInputForm]') || text.includes('USER_INPUT')) {
      console.log(`[Frontend] ${text}`);
    }
  });

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드\n');

    console.log('💬 메시지 전송: "호텔 예약하고 싶어요"\n');
    await page.fill('.input-box', '호텔 예약하고 싶어요');
    await page.click('.send-btn');

    // 응답 대기
    console.log('⏳ 응답 대기 중...\n');
    await page.waitForTimeout(10000);

    // 폼이 나타났는지 확인
    const formVisible = await page.isVisible('.user-input-form').catch(() => false);
    console.log(`\n폼 표시 여부: ${formVisible ? '✅ 표시됨' : '❌ 없음'}`);

    if (formVisible) {
      console.log('✅ 폼이 나타났습니다!');
    } else {
      console.log('❌ 폼이 나타나지 않았습니다. 에이전트가 텍스트로 응답한 것 같습니다.');

      // 마지막 어시스턴트 메시지 확인
      const lastMsg = await page.textContent('.message-bubble:last-child .message-content').catch(() => '');
      console.log('\n마지막 메시지:', lastMsg.substring(0, 500));
    }

    await page.screenshot({ path: 'test-capture-response.png', fullPage: true });
    console.log('\n스크린샷 저장: test-capture-response.png');

  } catch (error) {
    console.error('\n❌ 에러:', error.message);
    await page.screenshot({ path: 'test-capture-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
