"""
state/context_builder.py — TravelState 기반 컨텍스트 블록 생성

사용자 메시지에 state 정보를 주입하여 에이전트가 컨텍스트를 인식하게 합니다.
"""
import logging

from .models import TravelState

logger = logging.getLogger(__name__)


class ContextBuilder:
    """TravelState를 기반으로 에이전트 컨텍스트 블록을 생성한다."""

    def __init__(self, state: TravelState) -> None:
        self.state = state

    def build_context_block(self, user_message: str, thread_id: str = "") -> str:
        """
        state를 기반으로 컨텍스트 블록을 생성하여 사용자 메시지에 주입한다.

        Args:
            user_message: 원본 사용자 메시지
            thread_id: 로깅용 스레드 ID (선택)

        Returns:
            컨텍스트가 주입된 메시지 (또는 원본 메시지)
        """
        ctx_lines = self._build_travel_context_lines()
        pref_lines = self._build_preference_lines()

        if not ctx_lines and not pref_lines:
            return user_message

        sections = []
        if ctx_lines:
            sections.append("[현재 여행 컨텍스트 - 이미 확인된 정보]\n" + "\n".join(ctx_lines))
        if pref_lines:
            sections.append("[사용자 취향 - 이미 수집 완료]\n" + "\n".join(pref_lines))

        context_block = "\n\n".join(sections)
        enriched_message = f"{context_block}\n\n사용자 요청: {user_message}"

        if thread_id:
            logger.info(f"[{thread_id}] 컨텍스트 주입: travel={ctx_lines}, prefs={pref_lines}")

        return enriched_message

    def _build_travel_context_lines(self) -> list[str]:
        """travel_context 기반 컨텍스트 라인 생성."""
        tc = self.state.travel_context
        ui = self.state.ui_context
        lines = []

        if ui.selected_hotel_code:
            lines.append(f"- 선택된 호텔 코드: {ui.selected_hotel_code}")
        if ui.selected_flight_id:
            lines.append(f"- 선택된 항공편 ID: {ui.selected_flight_id}")
        if tc.destination:
            lines.append(f"- 목적지: {tc.destination}")
        if tc.origin:
            lines.append(f"- 출발지: {tc.origin}")
        if tc.check_in:
            lines.append(f"- 체크인/출발일: {tc.check_in}")
        if tc.check_out:
            lines.append(f"- 체크아웃/귀국일: {tc.check_out}")
        if tc.nights:
            lines.append(f"- 숙박: {tc.nights}박")
        if tc.guests:
            lines.append(f"- 인원: {tc.guests}명")
        if tc.rooms:
            lines.append(f"- 객실 수: {tc.rooms}실")
        if tc.trip_type:
            lines.append(f"- 여행 유형: {tc.trip_type}")
        if tc.budget_range:
            lines.append(f"- 예산 수준: {tc.budget_range}")
        if tc.travel_purpose:
            purpose_label = self._translate_travel_purpose(tc.travel_purpose)
            lines.append(f"- 여행 목적: {purpose_label}")

        return lines

    def _build_preference_lines(self) -> list[str]:
        """user_preferences 기반 취향 라인 생성."""
        pref = self.state.user_preferences
        lines = []

        hotel_pref_collected = any([pref.hotel_grade, pref.hotel_type, pref.amenities])
        if hotel_pref_collected:
            hotel_pref_parts = []
            if pref.hotel_grade:
                hotel_pref_parts.append(f"등급: {pref.hotel_grade}")
            if pref.hotel_type:
                hotel_pref_parts.append(f"유형: {pref.hotel_type}")
            if pref.amenities:
                hotel_pref_parts.append(f"편의시설: {', '.join(pref.amenities)}")
            lines.append(f"- 호텔 취향: {' / '.join(hotel_pref_parts)} [호텔 취향 수집 완료]")

        flight_pref_collected = any([pref.seat_class, pref.seat_position, pref.meal_preference, pref.airline_preference])
        if flight_pref_collected:
            flight_pref_parts = []
            if pref.seat_class:
                flight_pref_parts.append(f"좌석 등급: {pref.seat_class}")
            if pref.seat_position:
                flight_pref_parts.append(f"좌석 위치: {pref.seat_position}")
            if pref.meal_preference:
                flight_pref_parts.append(f"기내식: {pref.meal_preference}")
            if pref.airline_preference:
                flight_pref_parts.append(f"선호 항공사: {', '.join(pref.airline_preference)}")
            lines.append(f"- 항공 취향: {' / '.join(flight_pref_parts)} [항공 취향 수집 완료]")

        return lines

    @staticmethod
    def _translate_travel_purpose(purpose: str) -> str:
        """여행 목적 코드를 한글 라벨로 변환."""
        purpose_map = {
            "leisure": "여가/관광",
            "business": "비즈니스",
            "honeymoon": "허니문",
            "family": "가족 여행",
        }
        return purpose_map.get(purpose, purpose)
