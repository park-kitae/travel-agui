import pytest  # type: ignore[reportMissingImports]

from domains.travel.context import ContextBuilder
from domains.travel.state import TravelContext, TravelState, UIContext, UserPreferences


class TestContextBuilderEmptyState:
    """빈 state로 ContextBuilder 테스트."""

    def test_build_context_block_returns_original_message_when_empty_state(self):
        state = TravelState()
        builder = ContextBuilder(state)

        result = builder.build_context_block("안녕하세요")

        assert result == "안녕하세요"

    def test_build_context_block_no_travel_context_no_preferences(self):
        state = TravelState()
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천해줘")

        assert result == "호텔 추천해줘"


class TestContextBuilderTravelContext:
    """travel_context 기반 컨텍스트 주입 테스트."""

    def test_build_context_block_with_destination(self):
        state = TravelState(
            travel_context=TravelContext(destination="도쿄")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 찾아줘")

        assert "목적지: 도쿄" in result
        assert "사용자 요청: 호텔 찾아줘" in result

    def test_build_context_block_with_dates_and_guests(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                check_in="2026-06-10",
                check_out="2026-06-14",
                nights=4,
                guests=2,
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("항공편 알려줘")

        assert "목적지: 도쿄" in result
        assert "체크인/출발일: 2026-06-10" in result
        assert "체크아웃/귀국일: 2026-06-14" in result
        assert "숙박: 4박" in result
        assert "인원: 2명" in result

    def test_build_context_block_with_flight_origin(self):
        state = TravelState(
            travel_context=TravelContext(
                origin="서울",
                destination="오사카",
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("항공편 검색")

        assert "출발지: 서울" in result
        assert "목적지: 오사카" in result

    def test_build_context_block_with_rooms(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                rooms=2,
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 찾아줘")

        assert "객실 수: 2실" in result

    def test_build_context_block_with_trip_type(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                trip_type="round_trip",
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("항공편 알려줘")

        assert "여행 유형: round_trip" in result

    def test_build_context_block_with_budget_range(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                budget_range="고급",
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천해줘")

        assert "예산 수준: 고급" in result

    def test_build_context_block_with_travel_purpose(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                travel_purpose="honeymoon",
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 찾아줘")

        assert "여행 목적: 허니문" in result

    def test_build_context_block_with_all_purposes(self):
        purpose_map = {
            "leisure": "여가/관광",
            "business": "비즈니스",
            "honeymoon": "허니문",
            "family": "가족 여행",
        }

        for code, label in purpose_map.items():
            state = TravelState(
                travel_context=TravelContext(travel_purpose=code)
            )
            builder = ContextBuilder(state)
            result = builder.build_context_block("test")

            assert f"여행 목적: {label}" in result

    def test_build_context_block_with_unknown_purpose(self):
        state = TravelState(
            travel_context=TravelContext(travel_purpose="unknown_type")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("test")

        assert "여행 목적: unknown_type" in result


class TestContextBuilderUIContext:
    """ui_context 기반 컨텍스트 주입 테스트."""

    def test_build_context_block_with_selected_hotel_code(self):
        state = TravelState(
            ui_context=UIContext(selected_hotel_code="HTL-001")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("상세 정보 알려줘")

        assert "선택된 호텔 코드: HTL-001" in result

    def test_build_context_block_with_selected_flight_id(self):
        state = TravelState(
            ui_context=UIContext(selected_flight_id="FLT-123")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("예약해줘")

        assert "선택된 항공편 ID: FLT-123" in result


class TestContextBuilderUserPreferences:
    """user_preferences 기반 취향 주입 테스트."""

    def test_build_context_block_with_hotel_preferences(self):
        state = TravelState(
            user_preferences=UserPreferences(
                hotel_grade="5성",
                hotel_type="리조트",
                amenities=("수영장", "스파"),
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천")

        assert "호텔 취향: 등급: 5성 / 유형: 리조트 / 편의시설: 수영장, 스파" in result
        assert "[호텔 취향 수집 완료]" in result

    def test_build_context_block_with_partial_hotel_preferences(self):
        state = TravelState(
            user_preferences=UserPreferences(hotel_grade="4성")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천")

        assert "호텔 취향: 등급: 4성" in result

    def test_build_context_block_with_flight_preferences(self):
        state = TravelState(
            user_preferences=UserPreferences(
                seat_class="비즈니스",
                seat_position="창가",
                meal_preference="채식",
                airline_preference=("대한항공", "아시아나"),
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("항공편 검색")

        assert "좌석 등급: 비즈니스" in result
        assert "좌석 위치: 창가" in result
        assert "기내식: 채식" in result
        assert "선호 항공사: 대한항공, 아시아나" in result
        assert "[항공 취향 수집 완료]" in result

    def test_build_context_block_with_partial_flight_preferences(self):
        state = TravelState(
            user_preferences=UserPreferences(seat_class="이코노미")
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("항공편 검색")

        assert "항공 취향: 좌석 등급: 이코노미" in result

    def test_build_context_block_with_both_preferences(self):
        state = TravelState(
            user_preferences=UserPreferences(
                hotel_grade="5성",
                seat_class="비즈니스",
            )
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("추천해줘")

        assert "호텔 취향:" in result
        assert "항공 취향:" in result


class TestContextBuilderCombined:
    """travel_context + ui_context + user_preferences 조합 테스트."""

    def test_build_context_block_full_context(self):
        state = TravelState(
            travel_context=TravelContext(
                destination="도쿄",
                check_in="2026-06-10",
                guests=2,
            ),
            ui_context=UIContext(selected_hotel_code="HTL-001"),
            user_preferences=UserPreferences(
                hotel_grade="5성",
                seat_class="비즈니스",
            ),
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("상세 정보")

        assert "[현재 여행 컨텍스트 - 이미 확인된 정보]" in result
        assert "목적지: 도쿄" in result
        assert "체크인/출발일: 2026-06-10" in result
        assert "인원: 2명" in result
        assert "선택된 호텔 코드: HTL-001" in result
        assert "[사용자 취향 - 이미 수집 완료]" in result
        assert "호텔 취향:" in result
        assert "항공 취향:" in result
        assert "사용자 요청: 상세 정보" in result

    def test_build_context_block_structure(self):
        state = TravelState(
            travel_context=TravelContext(destination="도쿄"),
            user_preferences=UserPreferences(hotel_grade="4성"),
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천")

        lines = result.split("\n")
        travel_idx = next((i for i, line in enumerate(lines) if "현재 여행 컨텍스트" in line), -1)
        pref_idx = next((i for i, line in enumerate(lines) if "사용자 취향" in line), -1)
        user_idx = next((i for i, line in enumerate(lines) if "사용자 요청:" in line), -1)

        assert travel_idx < pref_idx < user_idx, "섹션 순서가 잘못되었습니다"

    def test_build_context_block_formats_sections_without_syntax_issues(self):
        state = TravelState(
            travel_context=TravelContext(destination="도쿄"),
            user_preferences=UserPreferences(hotel_grade="4성"),
        )
        builder = ContextBuilder(state)

        result = builder.build_context_block("호텔 추천")

        assert result == (
            "[현재 여행 컨텍스트 - 이미 확인된 정보]\n"
            "- 목적지: 도쿄\n\n"
            "[사용자 취향 - 이미 수집 완료]\n"
            "- 호텔 취향: 등급: 4성 [호텔 취향 수집 완료]\n\n"
            "사용자 요청: 호텔 추천"
        )


class TestContextBuilderEdgeCases:
    """엣지 케이스 테스트."""

    def test_build_context_block_empty_message(self):
        state = TravelState(travel_context=TravelContext(destination="도쿄"))
        builder = ContextBuilder(state)

        result = builder.build_context_block("")

        assert "목적지: 도쿄" in result
        assert "사용자 요청:" in result

    def test_build_context_block_whitespace_message(self):
        state = TravelState(travel_context=TravelContext(destination="도쿄"))
        builder = ContextBuilder(state)

        result = builder.build_context_block("   ")

        assert "목적지: 도쿄" in result
        assert "사용자 요청:" in result

    def test_build_context_block_with_thread_id_logging(self, caplog):
        import logging

        state = TravelState(travel_context=TravelContext(destination="도쿄"))
        builder = ContextBuilder(state)

        with caplog.at_level(logging.INFO):
            result = builder.build_context_block("test", thread_id="thread-123")

        assert "[thread-123] 컨텍스트 주입:" in caplog.text
