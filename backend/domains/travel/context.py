"""Travel domain context builder."""

from __future__ import annotations

import logging

from .state import TravelState

logger = logging.getLogger(__name__)


class ContextBuilder:
    """TravelState를 기반으로 에이전트 컨텍스트 블록을 생성한다."""

    def __init__(self, state: TravelState) -> None:
        self.state = state

    def build_context_block(self, user_message: str, thread_id: str = "") -> str:
        context_lines = self._build_travel_context_lines()
        preference_lines = self._build_preference_lines()

        if not context_lines and not preference_lines:
            return user_message

        sections: list[str] = []
        if context_lines:
            sections.append("[현재 여행 컨텍스트 - 이미 확인된 정보]\n" + "\n".join(context_lines))
        if preference_lines:
            sections.append("[사용자 취향 - 이미 수집 완료]\n" + "\n".join(preference_lines))

        context_block = "\n\n".join(sections)
        enriched_message = f"{context_block}\n\n사용자 요청: {user_message}"
        if thread_id:
            logger.info(f"[{thread_id}] 컨텍스트 주입: travel={context_lines}, prefs={preference_lines}")
        return enriched_message

    def _build_travel_context_lines(self) -> list[str]:
        travel_context = self.state.travel_context
        ui_context = self.state.ui_context
        lines: list[str] = []

        if ui_context.selected_hotel_code:
            lines.append(f"- 선택된 호텔 코드: {ui_context.selected_hotel_code}")
        if ui_context.selected_flight_id:
            lines.append(f"- 선택된 항공편 ID: {ui_context.selected_flight_id}")
        if travel_context.destination:
            lines.append(f"- 목적지: {travel_context.destination}")
        if travel_context.origin:
            lines.append(f"- 출발지: {travel_context.origin}")
        if travel_context.check_in:
            lines.append(f"- 체크인/출발일: {travel_context.check_in}")
        if travel_context.check_out:
            lines.append(f"- 체크아웃/귀국일: {travel_context.check_out}")
        if travel_context.nights:
            lines.append(f"- 숙박: {travel_context.nights}박")
        if travel_context.guests:
            lines.append(f"- 인원: {travel_context.guests}명")
        if travel_context.rooms:
            lines.append(f"- 객실 수: {travel_context.rooms}실")
        if travel_context.trip_type:
            lines.append(f"- 여행 유형: {travel_context.trip_type}")
        if travel_context.budget_range:
            lines.append(f"- 예산 수준: {travel_context.budget_range}")
        if travel_context.travel_purpose:
            lines.append(f"- 여행 목적: {self._translate_travel_purpose(travel_context.travel_purpose)}")

        return lines

    def _build_preference_lines(self) -> list[str]:
        preferences = self.state.user_preferences
        lines: list[str] = []

        if any((preferences.hotel_grade, preferences.hotel_type, preferences.amenities)):
            hotel_parts: list[str] = []
            if preferences.hotel_grade:
                hotel_parts.append(f"등급: {preferences.hotel_grade}")
            if preferences.hotel_type:
                hotel_parts.append(f"유형: {preferences.hotel_type}")
            if preferences.amenities:
                hotel_parts.append(f"편의시설: {', '.join(preferences.amenities)}")
            lines.append(f"- 호텔 취향: {' / '.join(hotel_parts)} [호텔 취향 수집 완료]")

        if any((preferences.seat_class, preferences.seat_position, preferences.meal_preference, preferences.airline_preference)):
            flight_parts: list[str] = []
            if preferences.seat_class:
                flight_parts.append(f"좌석 등급: {preferences.seat_class}")
            if preferences.seat_position:
                flight_parts.append(f"좌석 위치: {preferences.seat_position}")
            if preferences.meal_preference:
                flight_parts.append(f"기내식: {preferences.meal_preference}")
            if preferences.airline_preference:
                flight_parts.append(f"선호 항공사: {', '.join(preferences.airline_preference)}")
            lines.append(f"- 항공 취향: {' / '.join(flight_parts)} [항공 취향 수집 완료]")

        return lines

    @staticmethod
    def _translate_travel_purpose(purpose: str) -> str:
        purpose_map = {
            "leisure": "여가/관광",
            "business": "비즈니스",
            "honeymoon": "허니문",
            "family": "가족 여행",
        }
        return purpose_map.get(purpose, purpose)
