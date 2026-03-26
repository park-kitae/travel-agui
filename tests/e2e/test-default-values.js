// 기본값 테스트
const { chromium } = require('playwright');

(async () => {
  console.log('🧪 기본값 테스트 시작\n');

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

    // 1. 도시 언급 없이 호텔 요청
    console.log('=== 테스트 1: 도시 언급 없음 ===');
    await page.fill('.input-box', '호텔 예약하고 싶어요');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    await page.waitForTimeout(1000);

    // 필드 값 확인
    const city1 = await page.inputValue('input[id="city"]');
    const checkIn1 = await page.inputValue('input[id="check_in"]');
    const checkOut1 = await page.inputValue('input[id="check_out"]');
    const guests1 = await page.inputValue('input[id="guests"]');

    console.log('폼 기본값:');
    console.log(`  도시: "${city1}" ${city1 === '' ? '✅' : '❌ (빈값이어야 함)'}`);
    console.log(`  체크인: "${checkIn1}" ${checkIn1.length > 0 ? '✅' : '❌'}`);
    console.log(`  체크아웃: "${checkOut1}" ${checkOut1.length > 0 ? '✅' : '❌'}`);
    console.log(`  인원수: "${guests1}" ${guests1 === '2' ? '✅' : '❌ (2여야 함)'}`);

    // 날짜 차이 확인 (1박인지)
    if (checkIn1 && checkOut1) {
      const checkInDate = new Date(checkIn1);
      const checkOutDate = new Date(checkOut1);
      const diffDays = (checkOutDate - checkInDate) / (1000 * 60 * 60 * 24);
      console.log(`  날짜 차이: ${diffDays}일 ${diffDays === 1 ? '✅' : '❌ (1박이어야 함)'}`);
    }

    await page.screenshot({ path: 'test-default-no-city.png', fullPage: true });

    // 대화 초기화
    await page.click('.clear-btn');
    await page.waitForTimeout(1000);

    // 2. 도시 언급하며 호텔 요청
    console.log('\n=== 테스트 2: 도시 언급 (도쿄) ===');
    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    await page.waitForTimeout(1000);

    const city2 = await page.inputValue('input[id="city"]');
    const checkIn2 = await page.inputValue('input[id="check_in"]');
    const checkOut2 = await page.inputValue('input[id="check_out"]');
    const guests2 = await page.inputValue('input[id="guests"]');

    console.log('폼 기본값:');
    console.log(`  도시: "${city2}" ${city2 === '도쿄' ? '✅' : '❌ (도쿄여야 함)'}`);
    console.log(`  체크인: "${checkIn2}" ${checkIn2.length > 0 ? '✅' : '❌'}`);
    console.log(`  체크아웃: "${checkOut2}" ${checkOut2.length > 0 ? '✅' : '❌'}`);
    console.log(`  인원수: "${guests2}" ${guests2 === '2' ? '✅' : '❌ (2여야 함)'}`);

    await page.screenshot({ path: 'test-default-with-city.png', fullPage: true });

    console.log('\n✅ 모든 테스트 완료!');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n❌ 에러:', error.message);
    await page.screenshot({ path: 'test-default-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
