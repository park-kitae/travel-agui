// 항공편 폼 테스트
const { chromium } = require('playwright');

(async () => {
  console.log('✈️ 항공편 폼 테스트 시작\n');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 콘솔 로그 캡처
  page.on('console', msg => {
    if (msg.text().includes('[UserInputForm]')) {
      console.log(`[Frontend] ${msg.text()}`);
    }
  });

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드\n');

    // 테스트 1: 출발지/목적지 없이 항공편 요청
    console.log('=== 테스트 1: 항공편 검색 (출발지/목적지 없음) ===');
    await page.fill('.input-box', '항공편 검색하고 싶어요');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    await page.waitForTimeout(1000);

    // 폼 필드 확인
    const origin1 = await page.inputValue('input[id="origin"]');
    const destination1 = await page.inputValue('input[id="destination"]');
    const tripType1 = await page.inputValue('select[id="trip_type"]');
    const departureDate1 = await page.inputValue('input[id="departure_date"]');
    const returnDate1 = await page.inputValue('input[id="return_date"]');
    const passengers1 = await page.inputValue('input[id="passengers"]');

    console.log('폼 기본값:');
    console.log(`  출발지: "${origin1}" ${origin1 === '' ? '✅' : '❌'}`)  ;
    console.log(`  목적지: "${destination1}" ${destination1 === '' ? '✅' : '❌'}`);
    console.log(`  여행 유형: "${tripType1}" ${tripType1 === '왕복' ? '✅' : '❌'}`);
    console.log(`  출발 날짜: "${departureDate1}" ${departureDate1.length > 0 ? '✅' : '❌'}`);
    console.log(`  귀국 날짜: "${returnDate1}" ${returnDate1.length > 0 ? '✅' : '❌'}`);
    console.log(`  승객 수: "${passengers1}" ${passengers1 === '1' ? '✅' : '❌'}`);

    // 값 입력 후 제출
    await page.fill('input[id="origin"]', '서울');
    await page.fill('input[id="destination"]', '도쿄');
    await page.click('.form-submit-btn');

    // 사용자 메시지 확인
    await page.waitForTimeout(3000);

    const userMessages = await page.$$eval('.bubble-user',
      elements => elements.map(el => el.textContent)
    );
    const lastUserMessage = userMessages[userMessages.length - 1];
    console.log('\n사용자 메시지:', lastUserMessage);

    if (lastUserMessage.includes('왕복')) {
      console.log('✅ 왕복 항공편으로 표시됨');
    }
    if (lastUserMessage.includes('2026년')) {
      console.log('✅ 날짜가 자연어로 표시됨');
    }
    if (lastUserMessage.includes('서울에서 도쿄까지')) {
      console.log('✅ 출발지/목적지가 자연어 문장에 포함됨');
    }

    await page.screenshot({ path: 'test-flight-form.png', fullPage: true });

    // 대화 초기화
    await page.click('.clear-btn');
    await page.waitForTimeout(1000);

    // 테스트 2: 출발지/목적지 언급하며 항공편 요청
    console.log('\n=== 테스트 2: 항공편 검색 (서울→오사카) ===');
    await page.fill('.input-box', '서울에서 오사카 가는 항공편 알려줘');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    await page.waitForTimeout(1000);

    const origin2 = await page.inputValue('input[id="origin"]');
    const destination2 = await page.inputValue('input[id="destination"]');

    console.log('폼 기본값:');
    console.log(`  출발지: "${origin2}" ${origin2 === '서울' ? '✅' : '❌ (서울이어야 함)'}`);
    console.log(`  목적지: "${destination2}" ${destination2 === '오사카' ? '✅' : '❌ (오사카여야 함)'}`);

    await page.screenshot({ path: 'test-flight-with-cities.png', fullPage: true });

    console.log('\n✅ 모든 테스트 완료!');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n❌ 에러:', error.message);
    await page.screenshot({ path: 'test-flight-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
