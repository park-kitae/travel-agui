# Travel AI E2E 테스트 문서

## 개요
이 문서는 여행 AI 채팅 웹 애플리케이션의 Playwright E2E 테스트 시나리오를 설명합니다.

## 사전 준비

### 1. 서버 실행
테스트를 실행하기 전에 다음 서버들이 실행되어야 합니다:

```bash
# Backend A2A 서버 (포트 8001)
cd backend
source .venv/bin/activate
python a2a_server.py

# Frontend 개발 서버 (포트 5173)
cd frontend
npm run dev
```

### 2. 테스트 실행 위치
모든 테스트는 프로젝트 루트 디렉토리에서 실행해야 합니다:
```bash
cd /Users/kitaepark/project/agent/sample-agent/ag-ui-demo/travel-agui
```

---

## 테스트 시나리오

### 1. 전체 플로우 테스트 (test-full-flow.js)
**목적**: 호텔과 항공편 검색의 전체 플로우를 테스트

**시나리오**:
1. 호텔 검색 플로우:
   - "서울 호텔 알려줘" 입력
   - 호텔 입력 폼 표시 확인
   - 폼 제출 후 호텔 검색 결과 표시 확인

2. 항공편 검색 플로우:
   - "서울에서 도쿄 가는 항공편" 입력
   - 항공편 입력 폼 표시 확인
   - 폼 제출 후 왕복 항공편 결과 표시 확인 (출발편 + 귀국편)

**실행**:
```bash
node tests/e2e/test-full-flow.js
```

**예상 결과**:
- 호텔 폼이 표시되고 결과가 출력됨
- 항공편 폼이 표시되고 왕복편 결과가 출력됨
- 스크린샷 저장: `test-hotel-results.png`, `test-flight-results.png`

---

### 2. 호텔 직접 검색 테스트 (test-hotel-direct.js)
**목적**: 모든 정보를 포함한 호텔 검색 테스트

**시나리오**:
- "도쿄 호텔 추천해줘 (6월 10일~14일, 2명)" 입력
- 폼 없이 바로 호텔 검색 결과 표시

**실행**:
```bash
node tests/e2e/test-hotel-direct.js
```

**예상 결과**:
- 호텔 카드 1개, 호텔 아이템 3개 이상
- 스크린샷 저장: `test-hotel-direct.png`

---

### 3. 기본값 테스트 (test-default-values.js)
**목적**: 호텔 폼의 기본값 설정 확인

**시나리오**:
1. 도시가 포함된 경우:
   - "도쿄 호텔 알려줘" 입력
   - 폼의 도시 필드에 "도쿄"가 자동 입력됨

2. 도시가 없는 경우:
   - "호텔 추천해줘" 입력
   - 폼의 도시 필드가 빈 상태

**실행**:
```bash
node tests/e2e/test-default-values.js
```

**예상 결과**:
- 체크인: 3주 후 날짜
- 체크아웃: 체크인 + 1일
- 인원: 2명
- 도시: 컨텍스트에 따라 자동 입력 또는 빈 상태
- 스크린샷 저장: `test-default-with-city.png`, `test-default-no-city.png`

---

### 4. 자연어 메시지 테스트 (test-natural-language.js)
**목적**: 폼 제출 시 자연어로 변환된 메시지 표시 확인

**시나리오**:
- 호텔 폼 입력: 도쿄, 2026-04-16 ~ 2026-04-17, 2명
- 폼 제출 후 메시지 확인

**실행**:
```bash
node tests/e2e/test-natural-language.js
```

**예상 결과**:
- 사용자 메시지: "도쿄에서 2026년 4월 16일부터 2026년 4월 17일까지 2명이 숙박할 호텔을 검색합니다."
- 스크린샷 저장: `test-natural-language.png`

---

### 5. 항공편 폼 테스트 (test-flight-form.js)
**목적**: 항공편 입력 폼의 기본값과 왕복 옵션 확인

**시나리오**:
1. 도시가 포함된 경우:
   - "서울에서 도쿄 가는 항공편" 입력
   - 출발지 "서울", 목적지 "도쿄" 자동 입력

2. 도시가 없는 경우:
   - "항공편 알려줘" 입력
   - 출발지/목적지 빈 상태

**실행**:
```bash
node tests/e2e/test-flight-form.js
```

**예상 결과**:
- 출발 날짜: 1개월 후
- 귀국 날짜: 출발 + 7일
- 여행 유형: 왕복
- 승객 수: 1명
- 스크린샷 저장: `test-flight-with-cities.png`, `test-flight-form.png`

---

### 6. 폼 제출 테스트 (test-form-submit.js)
**목적**: 폼 제출 후 상태 변화 확인

**시나리오**:
- 호텔 폼에 값 입력
- 제출 버튼 클릭
- 폼이 사라지고 메시지가 표시되는지 확인

**실행**:
```bash
node tests/e2e/test-form-submit.js
```

**예상 결과**:
- 폼 제출 후 폼이 사라짐
- 사용자 메시지가 표시됨
- 스크린샷 저장: `test-form-submit-final.png`

---

### 7. 폼 값 확인 테스트 (test-form-values.js)
**목적**: 폼에 입력된 값 확인

**시나리오**:
- 호텔 폼의 모든 필드에 값 입력
- 각 필드의 값 확인

**실행**:
```bash
node tests/e2e/test-form-values.js
```

**예상 결과**:
- 모든 필드에 입력한 값이 정확히 반영됨
- 스크린샷 저장: `test-form-values.png`

---

### 8. 디버그 테스트 (test-debug.js)
**목적**: 이벤트 흐름 디버깅

**시나리오**:
- 메시지 전송 후 모든 이벤트 캡처
- 콘솔 로그 출력

**실행**:
```bash
node tests/e2e/test-debug.js
```

**예상 결과**:
- 모든 네트워크 이벤트와 콘솔 로그 출력

---

### 9. 응답 캡처 테스트 (test-capture-response.js)
**목적**: 서버 응답 상세 내용 확인

**시나리오**:
- 메시지 전송 후 SSE 응답 캡처
- 응답 내용 출력

**실행**:
```bash
node tests/e2e/test-capture-response.js
```

**예상 결과**:
- SSE 이벤트 스트림 캡처 및 출력
- 스크린샷 저장: `test-capture-response.png`

---

### 10. 응답 확인 테스트 (test-check-response.js)
**목적**: 특정 응답 패턴 확인

**시나리오**:
- 메시지 전송 후 응답 대기
- 특정 패턴의 응답 확인

**실행**:
```bash
node tests/e2e/test-check-response.js
```

**예상 결과**:
- 응답 패턴 확인
- 스크린샷 저장: `test-response-check.png`

---

## 스크린샷

모든 테스트 실행 후 스크린샷은 `tests/screenshots/` 디렉토리에 저장됩니다.

### 주요 스크린샷:
- `test-full-flow-error.png`: 전체 플로우 에러 화면
- `test-hotel-results.png`: 호텔 검색 결과 화면
- `test-flight-results.png`: 항공편 검색 결과 화면
- `test-hotel-direct.png`: 직접 호텔 검색 결과
- `test-default-with-city.png`: 도시가 포함된 폼
- `test-default-no-city.png`: 도시가 없는 폼
- `test-natural-language.png`: 자연어 메시지 화면
- `test-flight-with-cities.png`: 도시가 포함된 항공편 폼
- `test-flight-form.png`: 기본 항공편 폼

---

## 트러블슈팅

### 테스트 실패 시 확인사항:

1. **서버 실행 확인**:
   ```bash
   # Backend 확인
   curl http://localhost:8001/.well-known/agent-card.json

   # Frontend 확인
   curl http://localhost:5173
   ```

2. **포트 충돌 확인**:
   ```bash
   lsof -ti :8001  # Backend
   lsof -ti :5173  # Frontend
   ```

3. **테스트 타임아웃**:
   - 기본 타임아웃: 15초
   - LLM 응답이 느릴 경우 타임아웃 증가 필요

4. **스크린샷 확인**:
   - 테스트 실패 시 에러 스크린샷 확인
   - `tests/screenshots/` 디렉토리 참조

---

## 테스트 커버리지

현재 구현된 기능:
- ✅ 호텔 검색 (폼 입력)
- ✅ 항공편 검색 (폼 입력, 왕복)
- ✅ 기본값 자동 설정
- ✅ 자연어 메시지 변환
- ✅ 검색 결과 표시 (호텔, 항공편)
- ⚠️ 폼 제출 후 검색 결과 표시 (현재 이슈 있음)

---

## 다음 단계

1. **폼 → 검색 플로우 수정**:
   - LLM이 폼 제출 메시지를 인식하여 검색 함수 호출
   - instruction 최적화 필요

2. **추가 테스트 작성**:
   - 여행 팁 검색 테스트
   - 에러 핸들링 테스트
   - 여러 메시지 연속 전송 테스트

3. **CI/CD 통합**:
   - GitHub Actions 설정
   - 자동 테스트 실행

---

## 문의

테스트 관련 문의사항은 프로젝트 관리자에게 연락 바랍니다.
