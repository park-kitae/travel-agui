// 자연어 메시지 테스트
const { chromium } = require('playwright');

(async () => {
  console.log('🧪 자연어 메시지 테스트 시작\n');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드\n');

    // 테스트 1: 도시 없는 경우
    console.log('=== 테스트 1: 도시 없음 ===');
    await page.fill('.input-box', '호텔 예약하고 싶어요');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    await page.waitForTimeout(1000);

    // 폼에 도시 입력
    await page.fill('input[id="city"]', '서울');
    await page.click('.form-submit-btn');

    // 새로운 사용자 메시지가 나타날 때까지 대기
    await page.waitForTimeout(3000);

    // 모든 사용자 메시지 가져오기
    const userMessages = await page.$$eval('.bubble-user',
      elements => elements.map(el => el.textContent)
    );

    console.log('모든 사용자 메시지:', userMessages);
    const lastUserMessage = userMessages[userMessages.length - 1];
    console.log('마지막 사용자 메시지:', lastUserMessage);

    if (lastUserMessage.includes('2026년') && lastUserMessage.includes('월') && lastUserMessage.includes('일')) {
      console.log('✅ 날짜가 자연어로 표시됨');
    } else {
      console.log('❌ 날짜 형식 확인 필요');
    }

    if (lastUserMessage.includes('서울에서')) {
      console.log('✅ 도시가 자연어 문장에 포함됨');
    } else {
      console.log('❌ 도시 표현 확인 필요');
    }

    if (lastUserMessage.includes('명이 숙박할 호텔을 검색합니다')) {
      console.log('✅ 자연어 문장 형식 확인');
    } else {
      console.log('❌ 문장 형식 확인 필요');
    }

    await page.screenshot({ path: 'test-natural-language.png', fullPage: true });
    console.log('\n스크린샷 저장: test-natural-language.png');

    console.log('\n✅ 테스트 완료!');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n❌ 에러:', error.message);
    await page.screenshot({ path: 'test-natural-language-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
