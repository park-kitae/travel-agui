// 디버깅용 테스트 스크립트
const { chromium } = require('playwright');

(async () => {
  console.log('🔍 디버깅 테스트 시작...\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 콘솔 로그 캡처
  page.on('console', msg => {
    console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`);
  });

  // 네트워크 요청 모니터링
  page.on('request', request => {
    if (request.url().includes('/agui/')) {
      console.log(`[Network] → ${request.method()} ${request.url()}`);
    }
  });

  page.on('response', response => {
    if (response.url().includes('/agui/')) {
      console.log(`[Network] ← ${response.status()} ${response.url()}`);
    }
  });

  try {
    console.log('📍 Step 1: 페이지 접속');
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드 완료\n');

    console.log('📍 Step 2: 메시지 전송');
    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');
    console.log('✅ 메시지 전송 완료\n');

    console.log('📍 Step 3: 30초 동안 대기하며 상태 확인...\n');

    // 30초 동안 매 2초마다 상태 확인
    for (let i = 0; i < 15; i++) {
      await page.waitForTimeout(2000);

      const messages = await page.locator('.message-row').count();
      const formExists = await page.locator('.user-input-form').count();
      const toolCards = await page.locator('.tool-card').count();
      const hasError = await page.locator('.bubble-error').count();

      console.log(`[${(i + 1) * 2}초] 메시지: ${messages}개, 폼: ${formExists > 0 ? '✅' : '❌'}, 결과카드: ${toolCards}개, 에러: ${hasError > 0 ? '❌' : '✅'}`);

      if (formExists > 0) {
        console.log('\n✅ 폼이 나타났습니다!');

        // 폼 내용 확인
        const formHTML = await page.locator('.user-input-form').innerHTML();
        console.log('\n폼 HTML:\n', formHTML.substring(0, 500));

        // 스크린샷
        await page.screenshot({ path: 'test-form-appeared.png', fullPage: true });
        console.log('\n스크린샷 저장: test-form-appeared.png');
        break;
      }

      if (toolCards > 0) {
        console.log('\n⚠️  폼 없이 바로 결과가 나타났습니다.');
        await page.screenshot({ path: 'test-direct-result.png', fullPage: true });
        break;
      }

      if (hasError > 0) {
        console.log('\n❌ 에러 메시지가 나타났습니다.');
        const errorText = await page.locator('.bubble-error').first().textContent();
        console.log('에러 내용:', errorText);
        await page.screenshot({ path: 'test-error-message.png', fullPage: true });
        break;
      }
    }

    console.log('\n📍 Step 4: 최종 상태 확인');
    const allMessages = await page.locator('.message-row').all();
    console.log(`\n총 메시지 수: ${allMessages.length}`);

    for (let i = 0; i < allMessages.length; i++) {
      const role = await allMessages[i].locator('.avatar').first().textContent();
      const hasContent = await allMessages[i].locator('.bubble').count();
      const hasTool = await allMessages[i].locator('.tool-card').count();
      const hasForm = await allMessages[i].locator('.user-input-form').count();

      console.log(`  메시지 ${i + 1}: ${role} - 텍스트: ${hasContent > 0 ? '✅' : '❌'}, 툴카드: ${hasTool}, 폼: ${hasForm > 0 ? '✅' : '❌'}`);
    }

    // 마지막 스크린샷
    await page.screenshot({ path: 'test-final-state.png', fullPage: true });
    console.log('\n최종 스크린샷 저장: test-final-state.png');

    // 10초 더 대기
    console.log('\n⏳ 10초 더 대기...');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('\n❌ 에러 발생:', error.message);
    await page.screenshot({ path: 'test-debug-error.png', fullPage: true });
  } finally {
    await browser.close();
    console.log('\n✅ 테스트 종료');
  }
})();
