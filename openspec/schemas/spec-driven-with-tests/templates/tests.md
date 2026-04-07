## 테스트 계획

<!-- 이 문서는 specs의 시나리오와 tasks의 구현 항목을 기반으로 작성합니다. -->
<!-- 각 시나리오를 체크박스로 만들고, 테스트 실행 후 통과하면 [x]로 마킹합니다. -->

---

## Backend 테스트

<!-- 테스트 코드 위치: backend/tests/<change-name>/ -->

**실행 명령어:**
```bash
cd backend && uv run pytest tests/<change-name>/ -v
```

### [기능/모듈 이름]

| 파일 | 설명 |
|------|------|
| `test_<scenario>.py` | 시나리오 설명 |

#### 시나리오 체크리스트

- [ ] **시나리오명** — WHEN [조건] THEN [기대 결과]
- [ ] **시나리오명** — WHEN [조건] THEN [기대 결과]

---

## Frontend 테스트

<!-- 테스트 코드 위치: frontend/tests/e2e/<change-name>/ -->

**실행 명령어:**
```bash
cd frontend && npx playwright test tests/e2e/<change-name>/ --headed
```

### [기능/UI 이름]

| 파일 | 설명 |
|------|------|
| `<scenario>.spec.ts` | 시나리오 설명 |

#### 시나리오 체크리스트

- [ ] **시나리오명** — WHEN [조건] THEN [기대 결과]
- [ ] **시나리오명** — WHEN [조건] THEN [기대 결과]

---

## 테스트 요약

| 영역 | 전체 | 통과 | 실패 | 미실행 |
|------|------|------|------|--------|
| Backend | 0 | 0 | 0 | 0 |
| Frontend | 0 | 0 | 0 | 0 |
| **합계** | **0** | **0** | **0** | **0** |
