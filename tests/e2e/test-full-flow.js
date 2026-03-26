// 전체 플로우 테스트: 폼 제출 → 검색 결과 표시
const { chromium } = require('playwright');

(async () => {
  console.log('🧪 전체 플로우 테스트 시작\n');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드\n');

    // ==================== 테스트 1: 호텔 검색 ====================
    console.log('=== 테스트 1: 호텔 검색 ===');
    await page.fill('.input-box', '서울 호텔 알려줘');
    await page.click('.send-btn');

    // 폼 대기
    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 호텔 폼 나타남');

    await page.waitForTimeout(1000);

    // 날짜와 인원 확인 (기본값이 채워져 있어야 함)
    const city = await page.inputValue('input[id="city"]');
    console.log(`  도시: "${city}"`);

    // 폼 제출
    await page.click('.form-submit-btn');
    console.log('✅ 폼 제출됨');

    // 결과 카드 대기
    await page.waitForTimeout(5000);

    // 호텔 결과 확인
    const hotelCards = await page.$$('.tool-card');
    console.log(`호텔 결과 카드 수: ${hotelCards.length}`);

    const hotelItems = await page.$$('.hotel-item');
    console.log(`호텔 아이템 수: ${hotelItems.length}`);

    if (hotelItems.length > 0) {
      console.log('✅ 호텔 결과가 표시됨');
      const firstHotelName = await page.textContent('.hotel-item:first-child .hotel-name');
      console.log(`  첫 번째 호텔: ${firstHotelName}`);
    } else {
      console.log('❌ 호텔 결과가 표시되지 않음');
    }

    await page.screenshot({ path: 'test-hotel-results.png', fullPage: true });

    // 대화 초기화
    await page.click('.clear-btn');
    await page.waitForTimeout(1000);

    // ==================== 테스트 2: 항공편 검색 ====================
    console.log('\n=== 테스트 2: 항공편 검색 (왕복) ===');
    await page.fill('.input-box', '서울에서 도쿄 가는 항공편');
    await page.click('.send-btn');

    // 폼 대기
    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 항공편 폼 나타남');

    await page.waitForTimeout(1000);

    // 출발지/목적지 확인
    const origin = await page.inputValue('input[id="origin"]');
    const destination = await page.inputValue('input[id="destination"]');
    const tripType = await page.inputValue('select[id="trip_type"]');
    console.log(`  출발지: "${origin}"`);
    console.log(`  목적지: "${destination}"`);
    console.log(`  여행 유형: "${tripType}"`);

    // 폼 제출
    await page.click('.form-submit-btn');
    console.log('✅ 폼 제출됨');

    // 결과 대기
    await page.waitForTimeout(5000);

    // 항공편 결과 확인
    const flightCards = await page.$$('.tool-card');
    console.log(`항공편 결과 카드 수: ${flightCards.length}`);

    const flightItems = await page.$$('.flight-item');
    console.log(`항공편 아이템 수: ${flightItems.length}`);

    const flightSections = await page.$$('.flight-section');
    console.log(`항공편 섹션 수 (출발편/귀국편): ${flightSections.length}`);

    if (flightItems.length > 0) {
      console.log('✅ 항공편 결과가 표시됨');

      if (flightSections.length >= 2) {
        console.log('✅ 왕복 항공편 (출발편 + 귀국편) 표시됨');
      } else if (flightSections.length === 1) {
        console.log('⚠️ 편도 항공편만 표시됨');
      }

      const firstAirline = await page.textContent('.flight-item:first-child .airline-name');
      console.log(`  첫 번째 항공사: ${firstAirline}`);
    } else {
      console.log('❌ 항공편 결과가 표시되지 않음');
    }

    await page.screenshot({ path: 'test-flight-results.png', fullPage: true });

    console.log('\n✅ 전체 테스트 완료!');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n❌ 에러:', error.message);
    console.error(error.stack);
    await page.screenshot({ path: 'test-full-flow-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
